#!/usr/bin/env python3
import ccxt
import logging
from telegram.error import NetworkError, Unauthorized
import json, requests, urllib, time, datetime, sys, math, random
from pprint import pprint

def buy(currency, amount):
	print("buy "+currency+". Amount = "+str(amount))
	trade = {}
	trade["coin"] = currency
	trade["buy_price"] = random.uniform(1,10)
	trade["buy_date"] = str(datetime.datetime.now())

	jsonFile = open("trades.json", "r") 
	data = json.load(jsonFile) # Read the JSON into the buffer
	jsonFile.close()

	#print(data["trades"])
	data["trades"].append(trade)

	jsonFile = open("trades.json", "w+")
	jsonFile.write(json.dumps(data))
	jsonFile.close()

def sell(currency):
	print("sell "+currency)

	jsonFile = open("trades.json", "r") 
	data = json.load(jsonFile) # Read the JSON into the buffer
	jsonFile.close()

	for trade in reversed(data["trades"]):
		pprint(trade)
		if trade["coin"] == currency:
			trade["sell_price"] = random.uniform(1,10)
			trade["sell_date"] = str(datetime.datetime.now())
			trade["gains"] = (trade["buy_price"]-trade["sell_price"])/trade["buy_price"]

	jsonFile = open("trades.json", "w+")
	jsonFile.write(json.dumps(data))
	jsonFile.close()

buy("ETH",4.2)
sell("ETH")
time.sleep(0.5)

buy("RDD",random.uniform(1,100))

time.sleep(0.5)

buy("ETC",random.uniform(1,100))

time.sleep(0.5)
sell("ETC")

time.sleep(0.5)

buy("ETH",random.uniform(1,100))

sell("RDD")
time.sleep(0.5)

buy("XLM",random.uniform(1,100))
time.sleep(0.5)
sell("XLM")
sell("ETH")

jsonFile = open("trades.json", "r") # Open the JSON file for reading
data = json.load(jsonFile) # Read the JSON into the buffer
pprint(data)
jsonFile.close() # Close the JSON file