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
from random import randint

def asked_price(currencyPair,order_type):
    try:
        orderbook = exchange.fetch_order_book (currencyPair)
    except requests.exceptions.Timeout:
        print("ERROR : request timeout")
        sys.exit()
    except requests.exceptions.TooManyRedirects:
        print("ERROR : Too many redirect")
        sys.exit()
    except requests.exceptions.RequestException as e:
        print (e)
        sys.exit()
    if order_type == 'buy':
        price = orderbook['asks'][0][0] if len (orderbook['asks']) > 0 else sys.exit()
    elif order_type == 'sell':
        price = orderbook['bids'][0][0] if len (orderbook['bids']) > 0 else sys.exit()
    return price

# Retrieve credentials
credentials = json.load(open('credentials.json'))
exchange_name = "binance"
exchange = eval('ccxt.%s ()' % exchange_name)
exchange.apiKey = credentials["exchanges"][exchange_name]["api_key"]
exchange.secret = credentials["exchanges"][exchange_name]["secret"]


loop = True
markets_prev = []
winner = ""
buy_price = 0
while loop == True:
	markets_now = []
	try:
		markets = exchange.load_markets()
	except:
		print("Can't load marketlist")
		sys.exit()

	for market in markets:
		base,quote = market.split("/")
		if quote == "BTC":
			markets_now.append(market)

	if len(markets_prev) > 0:
		markets_prev.pop(randint(0,20))    # FOR TEST PURPOSES
		for market in markets_now:
			if market not in markets_prev:
				pprint("NEW ==> "+market)
				winner = market
				print("PASS MARKET BUY ORDER FOR "+market)
				buy_price = asked_price(market,"buy")
				print("BUY PRICE IS = "+str(buy_price))
				# PASS MARKET ORDER BUY
				loop = False
	markets_prev = markets_now
	for i in range(7,0,-1):
		sys.stdout.write("\rrestart in "+str(i)+" seconds")
		sys.stdout.flush()
		time.sleep(1)


for i in range(60,0,-1):
	sys.stdout.write("\rrestart in "+str(i)+" seconds (total 10 minutes)")
	sys.stdout.flush()
	time.sleep(1)
loop2 = True
while loop2 == True:
	sell_price = asked_price(winner,"sell")
	if sell_price > buy_price:
		#PASS SELL ORDER
		print("sell "+winner+" for "+str(sell_price))
		loop2 = False
	else:
		print("bought = "+str(buy_price)+". Current price = "+str(sell_price))

	for i in range(120,0,-1):
		sys.stdout.write("\rrestart in "+str(i)+" seconds")
		sys.stdout.flush()
		time.sleep(1)

print("COMPLETE")
sys.exit()