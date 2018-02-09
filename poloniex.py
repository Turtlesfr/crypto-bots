#!/usr/bin/env python3
import ccxt
import telegram
from telegram.ext import CommandHandler
from telegram.ext import Updater
import logging
from telegram.error import NetworkError, Unauthorized
import json, requests, urllib, time, datetime, sys

# Retrieve credentials
credentials = json.load(open('credentials.json'))

'''
exchange_name = ""
try:
    if sys.argv[1] is None:
        sys.exit()
except NameError:
    sys.exit()
else:
    if sys.argv[1] == "p" or sys.argv[1] == "poloniex":
    	exchange_name = "poloniex"
    elif sys.argv[1] == "g" or sys.argv[1] == "gateio":
    	exchange_name = "gateio"
    elif sys.argv[1] == "b" or sys.argv[1] == "binance":
    	exchange_name = "binance"
    else:
    	print("Exchange name not recognized")
    	sys.exit()
'''

exchange_name = "poloniex"

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
if len(sys.argv) >= 3:
	iterArgs = iter(sys.argv)
	next(iterArgs)
	next(iterArgs)
	for arg in iterArgs:
		c_force_buy.append(arg)

print(c_force_buy)

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
					try:
						exchange.cancel_order(order['id'])
					except:
						print("we catched an error")
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

#---------------------------------------------------------------

#LOAD OFFLINE___________________________________________________

alias_dict = json.load(open('alias.json'))
hodl_dict = json.load(open('hodl.json'))

#---------------------------------------------------------------

### START LOOP HERE=============================================
counter = 0
while counter < 100000:
	#DYNAMIC VARS
	c_feed = []
	log_file = open("log.txt", "a")
	#fh = open("currencies_owned.txt", "r+")
	#c_portfolio = fh.readlines()[len(fh.readlines())-1].split(",")

	#---------------------------------------------------------------

	#RETRIEVE feed DATA________________________________________
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
		else:
			print("\n")
			print(str(datetime.datetime.now()))
			print(entry['signature'])
	print('c_feed --> [%s]' % ','.join(map(str,c_feed)))
	log_file.write("\n "+"c_feed --> [%s]" % ",".join(map(str,c_feed)))

	#---------------------------------------------------------------

	#START THE JOB__________________________________________________
	log_file.write("\n")
	log_file.write("\n ------------------------------start------------------------------")
	log_file.write("\n "+str(datetime.datetime.now()))

	if counter == 0: # FIRST RUN : we just load c_initial
		for currency in c_feed:
			if currency not in c_force_buy:
				c_initial.append(currency)
		print('c_initial --> [%s]' % ','.join(map(str,c_initial)))
		print('c_force_buy --> [%s]' % ','.join(map(str,c_force_buy)))
		log_file.write("\n "+"c_initial --> [%s]" % ",".join(map(str,c_initial)))
		log_file.write("\n "+"c_force_buy --> [%s]" % ",".join(map(str,c_force_buy)))

	else:
		c_portfolio = {}
		c_to_keep = []
		c_to_sell = []
		c_to_buy = []
		cant_be_satisfied = []

		exchange = eval('ccxt.%s ()' % exchange_name)
		exchange.apiKey = credentials["exchanges"][exchange_name]["api_key"]
		exchange.secret = credentials["exchanges"][exchange_name]["secret"]
		orders = exchange.fetchOrders('ETH/BTC')
		print(orders)
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
			symbolBTC = key+"/BTC"
			if symbolBTC in markets:
				if (amount > 0) and (key!="USDT"):
					if alias(key) in hodl_dict[exchange_name]:
						#check if there is more than HODL amount
						if amount > hodl_dict[exchange_name][alias(key)]:
							if key == "BTC":
								if amount > 0.01:
									c_portfolio[key] = amount - hodl_dict[exchange_name][alias(key)]
							else:
								if amount - hodl_dict[exchange_name][alias(key)] > markets[key+"/BTC"]["limits"]["amount"]["min"]:
									symbol = key+"/BTC"
									price = asked_price(symbol,'sell')
									#print("symbol "+symbol+" price = "+str(price)+" amount = "+str(amount)+" price*amount = "+str(price*amount))
									if price*amount > 0.002:
										c_portfolio[key] = amount - hodl_dict[exchange_name][alias(key)]
					else:
						if key == "BTC":
							if amount > 0.01:
								c_portfolio[key] = amount
						else:
							if amount > markets[key+"/BTC"]["limits"]["amount"]["min"]:
								symbol = key+"/BTC"
								price = asked_price(symbol,'sell')
								#print("symbol "+symbol+" price = "+str(price)+" amount = "+str(amount)+" price*amount = "+str(price*amount))
								if price*amount > 0.002:
									c_portfolio[key] = amount
				elif key == "USDT":
					latest_usdt_balance = amount

		for coin in c_feed:
			if (coin not in c_initial) and (coin not in c_portfolio):
				if coin+"/BTC" in markets:
					c_to_buy.append(coin)
					print("coin to buy : "+coin)
				else:
					print(coin+" is not tradable on "+exchange_name)
					log_file.write("\n "+coin+" is not tradable on "+exchange_name)
			elif (coin not in c_initial) and (coin in c_portfolio):
				c_to_keep.append(coin)
			elif (coin in c_initial) and (coin not in c_portfolio):
				print(coin+" is a missed opportunity")
				log_file.write("\n "+coin+" is a missed opportunity")
				#old run, do nothing
		for coin in c_initial:
			if coin not in c_feed:
				c_initial.remove(coin)
		for coin in c_portfolio:
			if (coin not in c_feed) and (coin != "USDT"):
				if coin+"/BTC" in markets:
					min_amount = markets[coin+"/BTC"]["limits"]["amount"]["min"]
					if alias(coin) in hodl_dict[exchange_name]:
						available_for_sell = balance[coin] - hodl_dict[exchange_name][alias(coin)]
					else:
						available_for_sell = balance[coin]
					if available_for_sell > min_amount:
						c_to_sell.append(coin)
		print('c_initial --> [%s]' % ','.join(map(str,c_initial)))
		print('c_feed --> [%s]' % ','.join(map(str,c_feed)))
		print('c_portfolio --> [%s]' % ','.join(map(str,c_portfolio)))
		print('c_to_sell --> [%s]' % ','.join(map(str,c_to_sell)))
		print('c_to_keep --> [%s]' % ','.join(map(str,c_to_keep)))
		print('c_to_buy --> [%s]' % ','.join(map(str,c_to_buy)))

		log_file.write("\n "+"c_initial --> [%s]" % ",".join(map(str,c_initial)))
		log_file.write("\n "+"c_feed --> [%s]" % ",".join(map(str,c_feed)))
		log_file.write("\n "+"c_portfolio --> [%s]" % ",".join(map(str,c_portfolio)))
		log_file.write("\n "+"c_to_sell --> [%s]" % ",".join(map(str,c_to_sell)))
		log_file.write("\n "+"c_to_keep --> [%s]" % ",".join(map(str,c_to_keep)))
		log_file.write("\n "+"c_to_buy --> [%s]" % ",".join(map(str,c_to_buy)))
		
		###################################   SELL   ################################################
		for coin in c_to_sell:
			coin_balance = get_balance(coin)
			if coin+"/USDT" in markets:
				precision = markets[coin+"/USDT"]["precision"]["amount"]
				min_amount = markets[coin+"/USDT"]["limits"]["amount"]["min"]
				if alias(coin) in hodl_dict[exchange_name]:
					available_for_sell = coin_balance - hodl_dict[exchange_name][alias(coin)]
				else:
					available_for_sell = coin_balance
				if available_for_sell > min_amount:
					final_quantity = round(available_for_sell,precision)
					print("We will sell "+str(final_quantity)+" "+coin)
					log_file.write("\n We will sell "+str(final_quantity)+" "+coin)
					### PASS SELL ORDER in BTC
					symbol = coin+"/USDT"
					amount = final_quantity
					sell_order(symbol,amount)
				else:
					print("not enough "+coin+" to reach min amount ("+str(min_amount)+"). Available : "+str(available_for_sell))
					log_file.write("\n Not enough "+coin+" to reach min amount ("+str(min_amount)+"). Available : "+str(available_for_sell))
					c_portfolio.pop(coin)
			else:
				if coin+"/BTC" in markets:
					#print("Can sell "+coin+" for BTC")
					precision = markets[coin+"/BTC"]["precision"]["amount"]
					min_amount = markets[coin+"/BTC"]["limits"]["amount"]["min"]
					if alias(coin) in hodl_dict[exchange_name]:
						available_for_sell = coin_balance - hodl_dict[exchange_name][alias(coin)]
					else:
						available_for_sell = coin_balance
					if available_for_sell > min_amount:
						final_quantity = round(available_for_sell,precision)
						print("We will sell "+str(final_quantity)+" "+coin)
						log_file.write("\n We will sell "+str(final_quantity)+" "+coin)
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

		#####################################################   BUY   ################################################
		print('c_portfolio --> [%s]' % ','.join(map(str,c_portfolio)))
		log_file.write("\n "+"c_portfolio --> [%s]" % ",".join(map(str,c_portfolio)))
		print("portfolio length = "+str(len(c_portfolio)))
		USDT_balance = get_balance("USDT")
		if len(c_portfolio) == 0:
			allocated_budget = USDT_balance / 4
		elif 1<= len(c_portfolio) < 4:
			allocated_budget = USDT_balance / (4-len(c_portfolio))
		else:
			print("No budget, portfolio has too much items")
			allocated_budget = 0
			log_file.write("\n No budget, portfolio has too much items")

		print("allocated_budget  = "+str(allocated_budget))
		log_file.write("\n allocated_budget  = "+str(allocated_budget))
		if allocated_budget > 0:
			for coin in c_to_buy:
				if coin+"/USDT" in markets:
					precision = markets[coin+"/USDT"]["precision"]["amount"]
					min_amount = markets[coin+"/USDT"]["limits"]["amount"]["min"]

					price = asked_price(coin+"/USDT",'buy')
					if price*min_amount > allocated_budget:
						print("We don't have enough USDT to buy "+coin+". Needed = "+str(price*min_amount)+". Available = "+str(allocated_budget))
						log_file.write("\n We don't have enough USDT to buy "+coin+". Needed = "+str(price*min_amount)+". Available = "+str(allocated_budget))
					else:
						## PASS BUY ORDER in USDT
						amount = round((allocated_budget/price)*0.96,precision)
						print("We will buy "+str(amount)+" "+coin+" with "+str(allocated_budget)+" USDT")
						log_file.write("\n We will buy "+str(amount)+" "+coin+" with "+str(allocated_budget)+" USDT")
						symbol = coin+"/USDT"
						#exchange.create_market_buy_order (symbol, amount)
						buy_order(symbol,amount)

				elif coin+"/BTC" in markets:
					old_btc_balance = get_balance('BTC')
					
					# FIRST, buy BTC with USDT
					precision = markets["BTC/USDT"]["precision"]["amount"]
					min_amount = markets["BTC/USDT"]["limits"]["amount"]["min"]
					price = asked_price("BTC/USDT",'buy')
					if price*min_amount > allocated_budget:
						print("We don't have enough USDT to buy BTC")
						log_file.write("\n We don't have enough USDT to buy BTC")
					else:
						print("Let's buy some BTC (in order to buy "+coin+" after)")
						log_file.write("\n Let's buy some BTC (in order to buy "+coin+" after)")
						## BUY BTC with USDT
						amount = round((allocated_budget)/price*0.96,precision)
						symbol = "BTC/USDT"
						print("buy_order("+symbol+","+str(amount)+")")
						log_file.write("\n buy_order("+symbol+","+str(amount)+")")
						#exchange.create_market_buy_order (symbol, amount)
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
						log_file.write("\n We don't have enough BTC to buy "+coin+". Needed = "+str(price*min_amount)+". Available = "+str(btc_overflow))
					else:
						symbol = coin+"/BTC"
						amount = round((btc_overflow/price),precision)
						## PASS BUY ORDER in BTC
						print("buy_order("+symbol+","+str(amount)+")")
						log_file.write("\n buy_order("+symbol+","+str(amount)+")")
						buy_order(symbol,amount)
				else:
					print(coin+" is not tradable on "+exchange_name)
					log_file.write("\n "+coin+" is not tradable on "+exchange_name)
			
		tickers = get_tickers()
		balance = get_balances()
		balances = {}
		balances["BTC"] = 0
		balances["USDT"] = 0

		for key,value in c_portfolio.items():
			print(key+"==>"+str(value))
			coinSymbolUSDT = key+"/USDT"
			coinSymbolBTC = key+"/BTC"
			coinValue = 0
			if coinSymbolUSDT in tickers:
				coinValue = tickers[coinSymbolUSDT]["bid"]*value
				balances["USDT"] += coinValue
			elif coinSymbolBTC in tickers:
				coinValue = tickers[coinSymbolBTC]["bid"]*value*tickers["BTC/USDT"]["bid"]
				balances["USDT"] += coinValue
			print(key+" value in USDT = "+str(coinValue))

		print("USDT in wallet = "+str(balance["USDT"]))
		log_file.write("\n USDT in wallet = "+str(balance["USDT"]))
		all_balances = balances["USDT"] + balance["USDT"]
		print("Balance total = "+str(all_balances))
		log_file.write("\n Balance total = "+str(all_balances))

	print("================================================================ closing iteration n°"+str(counter))
	log_file.write("\n "+"================================================================ closing iteration n°"+str(counter))
	log_file.close()
	if counter == 0:
		print("time sleep 5")
		for i in range(5,0,-1):
			sys.stdout.write("\rrestart in "+str(i)+" seconds")
			sys.stdout.flush()
			time.sleep(1)
	else:
		print("time sleep 60")
		for i in range(60,0,-1):
			sys.stdout.write("\rrestart in "+str(i)+" seconds")
			sys.stdout.flush()
			time.sleep(1)
	counter += 1