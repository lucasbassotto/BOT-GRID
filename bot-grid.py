import hmac
import hashlib
import json
import requests
import time
import random
import numpy as np
import pygsheets
from threading import Thread

gc = pygsheets.authorize(service_file="future-arbitrage.json")
sh = gc.open("GRID CRYPTOCOM")

def cryptocom(method,p):
    API_KEY = "bL4NrTo1kkRfPzzqK2yfWW"
    SECRET_KEY = "MAg7p8sS5Z35xJu36bPHQK"
    base_url = "https://deriv-api.crypto.com/v1/"
    req = {
      "id": random.randint(1000000, 2000000),
      "method": method,
      "api_key": API_KEY,
      "params": p,
      "nonce": int(time.time() * 1000)
    }

    # First ensure the params are alphabetically sorted by key
    paramString = ""

    if "params" in req:
      for key in sorted(req['params']):
        paramString += key
        value = req['params'][key]
        if value is None:
          paramString += 'null'
        elif isinstance(value, list):
          paramString += ','.join(value)
        else:
          paramString += str(value)

    sigPayload = req['method'] + str(req['id']) + req['api_key'] + paramString + str(req['nonce'])

    req['sig'] = hmac.new(
      bytes(str(SECRET_KEY), 'utf-8'),
      msg=bytes(sigPayload, 'utf-8'),
      digestmod=hashlib.sha256
    ).hexdigest()
    r = requests.post(base_url+req['method'], json=req).json()
    print(r)
    return r

def btc_price():
    btc_price = requests.get("https://deriv-api.crypto.com/v1/public/get-tickers?instrument_name=BTCUSD-PERP").json()['result']['data'][0]['a']
    price = float(btc_price)
    return price

def desv_pad():
    candles = requests.get("https://deriv-api.crypto.com/v1/public/get-candlestick?instrument_name=BTCUSD-PERP&timeframe=M15&count=15").json()['result']['data']
    closes = []
    for x in candles:
        float(x['o'])
        closes.append(float(x['o']))
        std = np.std(closes)
    return std

def ordens_venda():
    precos_venda = sum(sh[0].get_values("N10","N19",returnas='matrix',value_render="UNFORMATTED_VALUE"),[])
    size_venda = sum(sh[0].get_values("P10","P19",returnas='matrix',value_render="UNFORMATTED_VALUE"),[])
    for preco, size in zip(precos_venda, size_venda):
        n = random.randint(1000000, 2000000)
        size = round(size,3)
            
        cryptocom("private/create-order",
                 {"instrument_name": "BTCUSD-PERP",
                "side": "SELL",
                "type": "LIMIT",
                "price": str(preco),
                "quantity": str(size),
                "exec_inst": ["POST_ONLY"],
                "client_oid": str(n),
                "time_in_force": "GOOD_TILL_CANCEL"})

        print('Posicionando VENDA', "size", size, "preco", preco, desv_pad())

def ordens_compra():
    precos_compra = sum(sh[0].get_values("I10","I19",returnas='matrix',value_render="UNFORMATTED_VALUE"),[])
    size_compra = sum(sh[0].get_values("K10","K19",returnas='matrix',value_render="UNFORMATTED_VALUE"),[])
    for preco, size in zip(precos_compra, size_compra):
        n = random.randint(1000000, 2000000)
        size = round(size,3)
        cryptocom("private/create-order",
                 {"instrument_name": "BTCUSD-PERP",
                "side": "BUY",
                "type": "LIMIT",
                "price": str(preco),
                "quantity": str(size),
                "exec_inst": ["POST_ONLY"],
                "client_oid": str(n),
                "time_in_force": "GOOD_TILL_CANCEL"})

        print('Posicionando COMPRA', "size", size, "preco", preco)

def stop_compra():
    precos_venda = sum(sh[0].get_values("N10","N19",returnas='matrix',value_render="UNFORMATTED_VALUE"),[])
    size_venda = sum(sh[0].get_values("P10","P19",returnas='matrix',value_render="UNFORMATTED_VALUE"),[])
    for preco, size in zip(precos_venda, size_venda):
        n = random.randint(1000000, 2000000)
        size = round(size,3)
    
        if btc_price() >= preco:
            ordertype = "TAKE_PROFIT_LIMIT"
        else:
            ordertype = 'STOP_LIMIT'
        
        cryptocom("private/create-order",
                {"instrument_name": "BTCUSD-PERP",
                "side": "BUY",
                "type": ordertype,
                "price": str(round(preco-desv_pad())),
                "quantity": str(size),
                "exec_inst": ["POST_ONLY"],
                "client_oid": str(n),
                "time_in_force": "GOOD_TILL_CANCEL",
                "ref_price": str(preco),
                "ref_price_type": "LAST_PRICE"})

        print('Posicionando compra stop', "size", size, "preco", preco, desv_pad())

def stop_venda():
    precos_compra = sum(sh[0].get_values("I10","I19",returnas='matrix',value_render="UNFORMATTED_VALUE"),[])
    size_compra = sum(sh[0].get_values("K10","K19",returnas='matrix',value_render="UNFORMATTED_VALUE"),[])
    for preco, size in zip(precos_compra, size_compra):
        n = random.randint(1000000, 2000000)
        size = round(size,3)
        
        if btc_price() <= preco:
            ordertype = "TAKE_PROFIT_LIMIT"
        else:
            ordertype = 'STOP_LIMIT'
        
        cryptocom("private/create-order",
                {"instrument_name": "BTCUSD-PERP",
                "side": "SELL",
                "type": ordertype,
                "price": str(round(preco+desv_pad())),
                "quantity": str(size),
                "exec_inst": ["POST_ONLY"],
                "client_oid": str(n),
                "time_in_force": "GOOD_TILL_CANCEL",
                "ref_price": str(preco),
                "ref_price_type": "LAST_PRICE"})

        print('Posicionando venda stop', "size", size, "preco", preco, desv_pad())

def cancel_order(cancel_type):
    cryptocom("private/cancel-all-orders",{"instrument_name": "BTCUSD-PERP", "type": cancel_type})
    print("ordens_canceladas")
    time.sleep(1)

def positions():
    positions = cryptocom("private/get-positions", {"instrument_name": "BTCUSD-PERP"})["result"]["data"]
    quantity = float(positions[0]["quantity"])
    return quantity

def montar():
    while True:
        mount = sh[0].get_value("M4")
        print(mount, desv_pad(), btc_price())
        if mount == 'GO':
            print('Montando Grid')
            cancel_order("LIMIT")    
            ordens_venda()
            ordens_compra()
            sh[0].update_value("M4","STOP")
        
        time.sleep(1)
        
def reposicionamento():
    while True:
        repos = sh[0].get_value("M3")
        print(repos)
        if repos == 'ON':
            print('Posicionando trigger')
            cancel_order("TRIGGER")
            stop_compra()
            stop_venda()
        
        time.sleep(900)

t1 = Thread(target = montar)
t2 = Thread(target = reposicionamento)
t1.start()
t2.start()