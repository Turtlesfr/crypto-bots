#!/usr/bin/env python3
import ccxt
import logging
from telegram.error import NetworkError, Unauthorized
import json, requests, urllib, time, datetime, sys, math
from pprint import pprint
import random

trades = []
log_file_trades = open("log_gateio_trades.txt", "a")
def buy(currency,amount):
	print("buy "+currency+". Amount = "+str(amount))
	trade = {}
	trade["coin"] = currency
	trade["buy_price"] = random.uniform(1,10)
	trade["buy_date"] = str(datetime.datetime.now())
	trades.append(trade)

buy("ETH",4.2)

def sell(currency):
	print("sell "+currency)
	for trade in reversed(trades):
		if trade["coin"] == currency:
			trade["sell_price"] = random.uniform(1,10)
			trade["sell_date"] = str(datetime.datetime.now())
			trade["gains"] = (trade["buy_price"]-trade["sell_price"])/trade["buy_price"]
			log_file_trades.write("\n -------------")
			log_file_trades.write("\nCoin : "+trade["coin"])
			log_file_trades.write("\nBuy date : "+trade["buy_date"])
			log_file_trades.write("\nBuy price : "+str(trade["buy_price"]))
			log_file_trades.write("\nSell date : "+trade["sell_date"])
			log_file_trades.write("\nSell price : "+str(trade["sell_price"]))
			log_file_trades.write("\nOperation : "+str(trade["gains"]))

sell("ETH")
pprint(trades)

time.sleep(2)

buy("RDD",random.uniform(1,100))

time.sleep(2)


time.sleep(2)

buy("ETC",random.uniform(1,100))

time.sleep(2)
sell("ETC")

time.sleep(2)

buy("ETH",random.uniform(1,100))

sell("RDD")
time.sleep(2)

buy("XLM",random.uniform(1,100))

time.sleep(2)
sell("XLM")
sell("ETH")
pprint(trades)

log_file_trades.close()