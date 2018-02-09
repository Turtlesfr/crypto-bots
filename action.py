#!/usr/bin/env python
import ccxt
import telegram
from telegram.ext import CommandHandler
from telegram.ext import Updater
import logging
from telegram.error import NetworkError, Unauthorized
import json, requests, urllib, time, datetime, sys

# Retrieve credentials
credentials = json.load(open('credentials.json'))

exchange_name = ""
try:
    if sys.argv[1] is None:
        sys.exit()
except NameError:
    sys.exit()
else:
    if sys.argv[1] == "p" or sys.argv[1] == "poloniex":
    	exchange_name = "poloniex"
    elif sys.argv[1] == "b" or sys.argv[1] == "binance":
    	exchange_name = "binance"
    else:
    	print("Exchange name not recognized")
    	sys.exit()

print("We are trading on "+exchange_name)

#TELEGRAM
updater = Updater(credentials["telegram"]["bots"][0])
dispatcher = updater.dispatcher
def balance(bot, update):
	bot.sendMessage(chat_id=update.message.chat_id, text=str(all_balances)+" USDT")
balance_handler = CommandHandler('balance', balance)
dispatcher.add_handler(balance_handler)
def portfolio(bot, update):
	bot.sendMessage(chat_id=update.message.chat_id, text=c_portfolio)
portfolio_handler = CommandHandler('portfolio', portfolio)
dispatcher.add_handler(portfolio_handler)
updater.start_polling()
#TELEGRAM

#STATIC VARS____________________________________________________

c_initial = []
c_owned = []
latest_usdt_balance = 0
c_force_buy = []
c_portfolio = {}
url = credentials["feed"]["url"]
#---------------------------------------------------------------
#DEF____________________________________________________________

def alias(currency_called):
	if currency_called in alias_dict:
		return alias_dict[currency_called]
	else:
		return currency_called
def hodl(currency_called):
	if currency_called in hodl_dict:
		return hodl_dict[currency_called]
	else:
		return 0
def is_on_exchange(exchange,currency_called):
	currency_pair = currency_called+"USDT"
	for entry in prices:
		if currency_pair in entry["symbol"]:
			return True
	return False
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def get_balances():
	try:
		balance = exchange.fetch_balance()
	except requests.exceptions.Timeout:
		print("ERROR : request timeout")
		sys.exit()
	except requests.exceptions.TooManyRedirects:
	    print("ERROR : Too many redirect")
	    sys.exit()
	except requests.exceptions.RequestException as e:
	    print (e)
	    sys.exit()
	return balance['free']

def get_balance(currency):
	asked_currency = currency
	try:
		balance = exchange.fetch_balance()
	except requests.exceptions.Timeout:
		print("ERROR : request timeout")
		sys.exit()
	except requests.exceptions.TooManyRedirects:
	    print("ERROR : Too many redirect")
	    sys.exit()
	except requests.exceptions.RequestException as e:
	    print (e)
	    sys.exit()
	return balance['free'][asked_currency]

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

def buy_order(currencyPair,amount):
	base = currencyPair.split('/')[0]
	quote = currencyPair.split('/')[1]
	precision = markets[currencyPair]["precision"]["amount"]
	print("precision : "+str(precision))
	min_amount = markets[currencyPair]["limits"]["amount"]["min"]
	print("New order : buy "+base+" with "+quote)
	# Setup targetBalance
	currentBalance = get_balance(base)
	targetBalance = currentBalance+amount
	fullfilled = False
	while fullfilled == False:
		# Cancel open orders
		openOrders = exchange.fetchOpenOrders(currencyPair)
		if len(openOrders) > 0:
			print("! there is already 1 or more open order for "+currencyPair)
			for order in openOrders:
				print("--> canceling order id "+order['id'])
				exchange.cancel_order(order['id'])
				time.sleep (exchange.rateLimit / 1000)
		# Create order
		# check Quote balance
		quoteBalance = get_balance(quote)
		orderAmount = round((targetBalance - currentBalance),precision)
		buy_price = asked_price(currencyPair,'buy')
		while quoteBalance < orderAmount*buy_price: #we don't have enough to buy
			orderAmount = orderAmount - orderAmount/100 #remove a bit
		if orderAmount > min_amount:
			print("create order as : exchange.create_limit_buy_order('"+currencyPair+"',"+str(orderAmount)+","+str(buy_price)+")")
			exchange.create_limit_buy_order(currencyPair,orderAmount,buy_price)
			time.sleep(4)
		else:
			print("orderAmount ("+str(orderAmount)+") is less than required min_amount ("+str(min_amount)+")")
		currentBalance = get_balance(base)
		print("new "+base+" balance is "+str(currentBalance))
		if currentBalance >= (targetBalance-(amount/100)):
			fullfilled = True
		
	print("--- Buy complete : "+base+" --> "+quote)

def sell_order(currencyPair,amount):
	base = currencyPair.split('/')[0]
	quote = currencyPair.split('/')[1]
	precision = markets[currencyPair]["precision"]["amount"]
	print("precision : "+str(precision))
	min_amount = markets[currencyPair]["limits"]["amount"]["min"]
	print("New order : sell "+base+" for "+quote)
	# Setup targetBalance
	currentBalance = get_balance(base)
	targetBalance = currentBalance-amount
	fullfilled = False
	if currentBalance >= amount:
		while fullfilled == False:
			# Cancel open orders
			openOrders = exchange.fetchOpenOrders(currencyPair)
			if len(openOrders) > 0:
				print("! there is already 1 or more open order for "+currencyPair)
				for order in openOrders:
					print("--> canceling order id "+order['id'])
					exchange.cancel_order(order['id'])
					time.sleep (exchange.rateLimit / 1000)
			# Create order
			orderAmount = round((currentBalance - targetBalance),precision)
			if orderAmount > min_amount:
				sell_price = asked_price(currencyPair,'sell')
				print("create order as : exchange.create_limit_sell_order('"+currencyPair+"',"+str(orderAmount)+","+str(sell_price)+")")
				exchange.create_limit_sell_order(currencyPair,orderAmount,sell_price)
				time.sleep(4)
			else:
				print("orderAmount ("+str(orderAmount)+") is less than required min_amount ("+str(min_amount)+")")
				fullfilled = True
			currentBalance = get_balance(base)
			print("new "+base+" balance is "+str(currentBalance))
			if currentBalance < (targetBalance-(amount/100)):
				fullfilled = True
		print("--- Sell complete : "+base+" --> "+quote)
	else:
		print("Unsufficient funds to pass sell order. Required = "+str(amount)+". Available = "+str(currentBalance))

def get_tickers():
	try:
		tickers = exchange.fetch_tickers()
	except requests.exceptions.Timeout:
		print("ERROR : request timeout")
		sys.exit()
	except requests.exceptions.TooManyRedirects:
	    print("ERROR : Too many redirect")
	    sys.exit()
	except requests.exceptions.RequestException as e:
	    print (e)
	    sys.exit()
	return tickers


id = exchange_name
exchange = eval('ccxt.%s ()' % id)
exchange.apiKey = credentials["exchanges"][exchange_name]["api_key"]
exchange.secret = credentials["exchanges"][exchange_name]["secret"]

try:
	markets = exchange.load_markets()
except requests.exceptions.Timeout:
	print("ERROR : request timeout")
	sys.exit()
except requests.exceptions.TooManyRedirects:
    print("ERROR : Too many redirect")
    sys.exit()
except requests.exceptions.RequestException as e:
    print (e)
    sys.exit()

budget = 50

if len(sys.argv) >= 3:
	iterArgs = iter(sys.argv)
	next(iterArgs)
	next(iterArgs)
	print(sys.argv[2]+" "+sys.argv[3])
	action = sys.argv[2]
	coin = sys.argv[3]
	if action == "buy":
		#buy
		if coin+"/USDT" in markets:
			precision = markets[coin+"/USDT"]["precision"]["amount"]
			min_amount = markets[coin+"/USDT"]["limits"]["amount"]["min"]
			price = asked_price(coin+"/USDT",'buy')
			if price*min_amount > budget:
				print("not rich enough")
			else:
				## PASS BUY ORDER in USDT
				amount = round((budget/price)*0.96,precision)
				print("We will buy "+str(amount)+" "+coin+" with "+str(budget)+" USDT")
				symbol = coin+"/USDT"
				#exchange.create_market_buy_order (symbol, amount)
				buy_order(symbol,amount)
		elif coin+"/BTC" in markets:
			old_btc_balance = get_balance('BTC')
			
			# FIRST, buy BTC with USDT
			precision = markets["BTC/USDT"]["precision"]["amount"]
			min_amount = markets["BTC/USDT"]["limits"]["amount"]["min"]
			price = asked_price("BTC/USDT",'buy')
			if price*min_amount > budget:
				print("We don't have enough USDT to buy BTC")
			else:
				print("Let's buy some BTC (in order to buy "+coin+" after)")
				## BUY BTC with USDT
				amount = round((budget)/price*0.96,precision)
				symbol = "BTC/USDT"
				print("buy_order("+symbol+","+str(amount)+")")
				buy_order(symbol,amount)
			time.sleep(3)
			# SECOND, Retrieve newly bought BTC

			new_balance = get_balance('BTC')
			btc_overflow = new_balance - old_btc_balance
			# THIRD, Buy currency with those BTC
			precision = markets[coin+"/BTC"]["precision"]["amount"]
			min_amount = markets[coin+"/BTC"]["limits"]["amount"]["min"]

			price = asked_price(coin+"/BTC",'buy')
			if price*min_amount > btc_overflow:
				print("We don't have enough BTC to buy "+coin+". Needed = "+str(price*min_amount)+". Available = "+str(btc_overflow))
			else:
				symbol = coin+"/BTC"
				amount = round((btc_overflow/price),precision)
				## PASS BUY ORDER in BTC
				print("buy_order("+symbol+","+str(amount)+")")
				buy_order(symbol,amount)
		else:
			print("coin not on "+exchange_name)
	elif action == "sell":
		coin_balance = get_balance(coin)
		if coin+"/USDT" in markets:
			precision = markets[coin+"/USDT"]["precision"]["amount"]
			min_amount = markets[coin+"/USDT"]["limits"]["amount"]["min"]
			available_for_sell = coin_balance
			if available_for_sell > min_amount:
				final_quantity = round(available_for_sell,precision)
				print("We will sell "+str(final_quantity)+" "+coin)
				### PASS SELL ORDER in BTC
				symbol = coin+"/USDT"
				amount = final_quantity
				sell_order(symbol,amount)
			else:
				print("not enough "+coin+" to reach min amount ("+str(min_amount)+"). Available : "+str(available_for_sell))
		else:
			if coin+"/BTC" in markets:
				precision = markets[coin+"/BTC"]["precision"]["amount"]
				min_amount = markets[coin+"/BTC"]["limits"]["amount"]["min"]
				available_for_sell = coin_balance
				if available_for_sell > min_amount:
					final_quantity = round(available_for_sell,precision)
					print("We will sell "+str(final_quantity)+" "+coin)
					#record current BTC balance
					old_btc_balance = get_balance('BTC')
					### PASS SELL ORDER in BTC
					symbol = coin+"/BTC"
					amount = final_quantity
					#exchange.create_market_sell_order (symbol, amount)
					sell_order(symbol,amount)
					time.sleep(3)

					new_balance = get_balance('BTC')
					btc_overflow = new_balance - old_btc_balance
					### PASS SELL ORDER in USDT
					symbol = "BTC/USDT"
					amount = btc_overflow
					#exchange.create_market_sell_order (symbol, amount)
					sell_order(symbol,amount)
				else:
					print("Not enough "+coin+" to reach min amount ("+str(min_amount)+"). Available : "+str(available_for_sell))
					log_file.write("\n Not enough "+coin+" to reach min amount ("+str(min_amount)+"). Available : "+str(available_for_sell))
					c_portfolio.pop(coin)

#print(c_force_buy)


#---------------------------------------------------------------

#LOAD OFFLINE___________________________________________________

alias_dict = json.load(open('alias.json'))
hodl_dict = json.load(open('hodl.json'))

#---------------------------------------------------------------

c_portfolio = {}
c_to_keep = []
c_to_sell = []
c_to_buy = []
cant_be_satisfied = []



#load markets
try:
	markets = exchange.load_markets()
except requests.exceptions.Timeout:
	print("ERROR : request timeout")
	sys.exit()
except requests.exceptions.TooManyRedirects:
    print("ERROR : Too many redirect")
    sys.exit()
except requests.exceptions.RequestException as e:
    print (e)
    sys.exit()

balance = get_balances()
for key,amount in balance.items():
	if (amount > 0) and (key!="USDT"):
		if alias(key) in hodl_dict[exchange_name]:
			#check if there is more than HODL amount
			if amount > hodl_dict[exchange_name][alias(key)]:
				if key == "BTC":
					if amount > 0.01:
						c_portfolio[key] = amount - hodl_dict[exchange_name][alias(key)]
				else:
					if amount - hodl_dict[exchange_name][alias(key)] > markets[key+"/BTC"]["limits"]["amount"]["min"]:
						c_portfolio[key] = amount - hodl_dict[exchange_name][alias(key)]
		else:
			if key == "BTC":
				if amount > 0.01:
					c_portfolio[key] = amount
			else:
				if amount > markets[key+"/BTC"]["limits"]["amount"]["min"]:
					c_portfolio[key] = amount
	elif key == "USDT":
		latest_usdt_balance = amount
sys.exit()
