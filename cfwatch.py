#!/usr/bin/env python3
import ccxt
import telegram
from telegram.ext import CommandHandler
from telegram.ext import Updater
import logging
from telegram.error import NetworkError, Unauthorized
import json, requests, urllib, time, datetime, sys, math
from pprint import pprint
from coinmarketcap import Market

# Retrieve credentials
credentials = json.load(open('credentials.json'))

coinmarketcap = Market()
alias_dict = json.load(open('alias.json'))
c_portfolio = ['ETH','LSK']
c_initial = []
c_feed = []
url = credentials["feed"]["url"]

def alias(currency_called):
    if currency_called in alias_dict:
        return alias_dict[currency_called]
    else:
        return currency_called

def get_price(coin):
    tickers = coinmarketcap.ticker()
    price = 0
    for ticker in tickers:
        if ticker["symbol"] == alias(coin):
            price = ticker["price_usd"]
    return price


 #RETRIEVE feed DATA________________________________________

counter = 0
while counter < 100000:
    c_to_buy = []
    c_to_sell = []
    try:
        feeddata = requests.get(url).json()
    except requests.exceptions.Timeout:
            print("ERROR : request timeout")
            sys.exit()
    except requests.exceptions.TooManyRedirects:
        print("ERROR : Too many redirect")
        sys.exit()
    except requests.exceptions.RequestException as e:
        print (e)
        sys.exit()

    for entry in feeddata:
        if 'signature' not in entry:
            if entry['name'] != 'USDT':
                c_feed.append(alias(entry['name']))

    if counter == 0: # FIRST RUN : we just load c_initial
        for currency in c_feed:
            c_initial.append(currency)
    else:
        c_feed.append("BTC")
        c_feed.append("LSK")
        for coin in c_initial:
            if coin not in c_feed:
                c_initial.remove(coin)
        for coin in c_feed:
            if (coin not in c_portfolio) and (coin not in c_initial):
                print("TB : "+coin)
                c_to_buy.append(coin)
        for coin in c_portfolio:
            if coin not in c_feed:
                print(coin)
                c_to_sell.append(coin)

        for coin in c_to_sell:
            c_portfolio.remove(coin)
            sell_price = get_price(coin)
            #LOG TRADE IN JSON
            jsonFile = open("trades_watch.json", "r") 
            data = json.load(jsonFile) # Read the JSON into the buffer
            jsonFile.close()

            for trade in reversed(data["trades"]):
                if trade["coin"] == coin:
                    trade["sell_price"] = sell_price
                    trade["sell_date"] = str(datetime.datetime.now())
                    trade["gains"] = (trade["sell_price"]-trade["buy_price"])/trade["buy_price"]
                    break
            jsonFile = open("trades_watch.json", "w+")
            jsonFile.write(json.dumps(data))
            jsonFile.close()

        for coin in c_to_buy:
            c_portfolio.append(coin)
            buy_price = get_price(coin)
            trade = {}

            trade["coin"] = coin
            trade["buy_price"] = buy_price
            trade["buy_date"] = str(datetime.datetime.now())

            jsonFile = open("trades_watch.json", "r") 
            data = json.load(jsonFile) # Read the JSON into the buffer
            jsonFile.close()
            for trade in reversed(data["trades"]):
                if trade["coin"] == coin:
                    if trade["sell_price"] in trade:
                        print("trade already registered")
                    else:
                        #print(data["trades"])
                        data["trades"].append(trade)
                        jsonFile = open("trades_watch.json", "w+")
                        jsonFile.write(json.dumps(data))
                        jsonFile.close()
    if counter == 0:
        for i in range(5,0,-1):
            sys.stdout.write("\rrestart in "+str(i)+" seconds")
            sys.stdout.flush()
            time.sleep(1)
    else:
        for i in range(10,0,-1):
            sys.stdout.write("\rrestart in "+str(i)+" seconds")
            sys.stdout.flush()
            time.sleep(1)
    counter += 1