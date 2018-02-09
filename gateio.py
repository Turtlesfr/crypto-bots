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
exchange_name = "gateio"

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
c_force_sell = []
c_portfolio = {}
url = credentials["feed"]["url"]
minimum_BTC_value_for_portfolio = 0.002
minimum_USD_value_for_portfolio = 15
trades = []

#---------------------------------------------------------------

if len(sys.argv) >= 3:
    iterArgs = iter(sys.argv)
    next(iterArgs)
    next(iterArgs)
    for arg in iterArgs:
        if arg[0] == "-":
            c_force_sell.append(arg[1:])
        else:
            c_force_buy.append(arg)

print(c_force_sell)
print(c_force_buy)

coinmarketcap = Market()

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
    order_complete = False
    base = currencyPair.split('/')[0]
    quote = currencyPair.split('/')[1]
    precision = markets[currencyPair]["precision"]["amount"]
    print("precision : "+str(precision))
    min_amount = markets[currencyPair]["limits"]["amount"]["min"]
    completed = 0
    buy_price = 0
    tries = 0
    while order_complete != True:
        order_amount = amount - completed
        price = asked_price(currencyPair,'buy')
        buy_price = price
        if order_amount > min_amount:
            if tries < 7:
                print("New order : buy "+base+" with "+quote)
                print("create order as : exchange.create_limit_buy_order('"+currencyPair+"',"+str(order_amount)+","+str(price)+")")
                try:
                    exchange.create_limit_buy_order(currencyPair,order_amount,price)
                except:
                    print("Error while creating buy order")
                    pass
                tries += 1
                time.sleep(3)
                cancel_all_orders()
                #check if completed
                balance = get_balance(base)
                if balance >= amount*0.95:
                    print("--- Buy complete : "+base+" --> "+quote)
                    order_complete = True
                else:
                    order_complete = False
                    completed = amount - balance
            else:
                print("too many tries, continue")
                order_complete = True
        else:
            print("buy impossible : min_amount not reached")
            order_complete = True
    # LOG TRADE IN JSON
    trade = {}
    trade["coin"] = base
    trade["buy_price"] = buy_price
    trade["buy_date"] = str(datetime.datetime.now())

    jsonFile = open("trades.json", "r") 
    data = json.load(jsonFile) # Read the JSON into the buffer
    jsonFile.close()
    for trade in reversed(data["trades"]):
        if trade["coin"] == base:
            if trade["sell_price"] in trade:
                print("trade already registered")
            else:
                #print(data["trades"])
                data["trades"].append(trade)
                jsonFile = open("trades.json", "w+")
                jsonFile.write(json.dumps(data))
                jsonFile.close()
    
    
def sell_order(currencyPair,amount):
    order_complete = False
    base = currencyPair.split('/')[0]
    quote = currencyPair.split('/')[1]
    precision = markets[currencyPair]["precision"]["amount"]
    print("precision : "+str(precision))
    min_amount = markets[currencyPair]["limits"]["amount"]["min"]
    sell_price = 0
    completed = 0
    tries = 0
    buy_price = 0
    gains = 0

    jsonFile = open("trades.json", "r") 
    data = json.load(jsonFile) # Read the JSON into the buffer
    jsonFile.close()
    for trade in reversed(data["trades"]):
        if trade["coin"] == base:
            buy_price = trade["buy_price"]
            print("Our buy price for "+base+" was "+str(buy_price))
            break
    sell_price = asked_price(currencyPair,'sell')
    price = sell_price
    if buy_price == 0:
        gains = -100
    else:
        gains = (sell_price - buy_price)/buy_price
    if gains > -0.015:
        while order_complete != True:
            order_amount = amount - completed
            sell_price = asked_price(currencyPair,'sell')
            if tries < 7:
                if order_amount > min_amount:
                    print("New order : sell "+base+" for "+quote)
                    print("create order as : exchange.create_limit_sell_order('"+currencyPair+"',"+str(order_amount)+","+str(price)+")")
                    try:
                        exchange.create_limit_sell_order(currencyPair,order_amount,price)
                    except:
                        print("Error while creating sell order")
                        pass
                    tries += 1
                    time.sleep(3)
                    cancel_all_orders()
                    #check if completed
                    balance = get_balance(base)
                    completed = amount - balance
                    if balance <= amount*0.95:
                        print("--- Sell complete: "+base+" --> "+quote)
                        order_complete = True
                        
                        #LOG TRADE IN JSON
                        jsonFile = open("trades.json", "r") 
                        data = json.load(jsonFile) # Read the JSON into the buffer
                        jsonFile.close()

                        for trade in reversed(data["trades"]):
                            if trade["coin"] == base:
                                trade["sell_price"] = sell_price
                                trade["sell_date"] = str(datetime.datetime.now())
                                trade["gains"] = (trade["sell_price"]-trade["buy_price"])/trade["buy_price"]
                                break

                        jsonFile = open("trades.json", "w+")
                        jsonFile.write(json.dumps(data))
                        jsonFile.close()
                else:
                    print("sell impossible : min_amount not reached")
            else:
                print("too many tries, continue")
                order_complete = True
    else:
        print("Gains are negative ==> HODL. gains so far on this trade = "+str(gains))
        order_complete = True
            
    

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
def cancel_all_orders():
    order_ids = []
    try:
        orders = exchange.privatePostOpenOrders()
    except:
        print("no order to cancel")
    #print(orders)
    if len(orders) > 0:
        for order in orders["orders"]:
            order_ids.append(order["orderNumber"])
        for orderId in order_ids:
            print(orderId)
            time.sleep(1)
            print("Canceling order n°"+orderId)
            try:
                exchange.cancelOrder(orderId)
            except:
                print("whatever")
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
    log_file = open("log_gateio.txt", "a")
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
        print('c_force_sell --> [%s]' % ','.join(map(str,c_force_sell)))
        log_file.write("\n "+"c_initial --> [%s]" % ",".join(map(str,c_initial)))
        log_file.write("\n "+"c_force_buy --> [%s]" % ",".join(map(str,c_force_buy)))
        log_file.write("\n "+"c_force_sell --> [%s]" % ",".join(map(str,c_force_sell)))

    else:
        c_portfolio = {}
        c_to_keep = []
        c_to_sell = []
        c_to_buy = []
        cant_be_satisfied = []

        exchange = eval('ccxt.%s ()' % exchange_name)
        exchange.apiKey = credentials["exchanges"][exchange_name]["api_key"]
        exchange.secret = credentials["exchanges"][exchange_name]["secret"]
        try:
            market_list = exchange.public_get_marketlist()
        except:
            print("Can't load marketlist")
            sys.exit()
        
        cancel_all_orders()
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

        # SELL IF FORCE SELL
        for coin in c_force_sell:
            coin_balance = get_balance(coin)
            if coin+"/USDT" in markets:
                precision = markets[coin+"/USDT"]["precision"]["amount"]
                min_amount = markets[coin+"/USDT"]["limits"]["amount"]["min"]
                available_for_sell = coin_balance
                if available_for_sell > min_amount:
                    final_quantity = round(available_for_sell,precision)
                    print("We will sell "+str(final_quantity)+" "+coin)
                    log_file.write("\n We will sell "+str(final_quantity)+" "+coin)
                    symbol = coin+"/USDT"
                    amount = final_quantity
                    sell_order(symbol,amount)
                else:
                    print("not enough "+coin+" to reach min amount ("+str(min_amount)+"). Available : "+str(available_for_sell))
                    log_file.write("\n Not enough "+coin+" to reach min amount ("+str(min_amount)+"). Available : "+str(available_for_sell))
                    if coin in c_portfolio:
                        c_portfolio.pop(coin)
            else:
                pritn("Can't sell "+coin+" because there is no "+coin+"+/USDT market on "+exchange_name)

        balance = get_balances()
        tickers = coinmarketcap.ticker()
        for key,amount in balance.items():
            symbolUSDT = key+"/USDT" # WE TRADE AGAINST USDT ONLY
            if amount > 0.002:
                if key == "BTC":
                    if amount > minimum_BTC_value_for_portfolio:
                        c_portfolio[key] = amount
                elif key == "USDT":
                    latest_usdt_balance = amount
                else:
                    if key == "IOTA":
                        key = "MIOTA"
                    for ticker in tickers:
                        if ticker["symbol"] == key:
                            USDvalue = float(amount)*float(ticker["price_usd"])
                            if USDvalue > minimum_USD_value_for_portfolio :
                                if key == "MIOTA":
                                    key = "IOTA"
                                c_portfolio[key] = amount

        for coin in c_feed:
            if (coin not in c_initial) and (coin not in c_portfolio):
                if coin+"/USDT" in markets:
                    c_to_buy.append(coin)
                    print("New coin to buy : "+coin)
                else:
                    print(coin+" is not tradable in USDT on "+exchange_name)
                    log_file.write("\n "+coin+" is not tradable in USDT on "+exchange_name)
            elif (coin not in c_initial) and (coin in c_portfolio):
                c_to_keep.append(coin)
            elif coin in c_initial:
                print(coin+" is a missed opportunity")
                log_file.write("\n "+coin+" is a missed opportunity")
                #old run, do nothing
        for coin in c_initial:
            if coin not in c_feed:
                c_initial.remove(coin)
        for coin in c_portfolio:
            if coin not in c_feed:
                min_amount = markets[coin+"/USDT"]["limits"]["amount"]["min"]
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
                available_for_sell = coin_balance
                if available_for_sell > min_amount:
                    final_quantity = round(available_for_sell,precision)
                    while final_quantity > available_for_sell:
                        final_quantity -= final_quantity*0.05
                        final_quantity = round(final_quantity,precision)
                    print("We will sell "+str(final_quantity)+" "+coin)
                    log_file.write("\n We will sell "+str(final_quantity)+" "+coin)
                    symbol = coin+"/USDT"
                    amount = final_quantity
                    sell_order(symbol,amount)
                    c_portfolio.pop(coin)
                else:
                    print("not enough "+coin+" to reach min amount ("+str(min_amount)+"). Available : "+str(available_for_sell))
                    log_file.write("\n Not enough "+coin+" to reach min amount ("+str(min_amount)+"). Available : "+str(available_for_sell))
                    c_portfolio.pop(coin)

        #####################################################   BUY   ################################################
        print('c_portfolio --> [%s]' % ','.join(map(str,c_portfolio)))
        log_file.write("\n "+"c_portfolio --> [%s]" % ",".join(map(str,c_portfolio)))
        print("portfolio length = "+str(len(c_portfolio)))
        time.sleep(2)
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
                        c_portfolio[coin] = amount
                else:
                    print(coin+" is not tradable in USDT on "+exchange_name)
                    log_file.write("\n "+coin+" is not tradable in USDT on "+exchange_name)
            
        tickers = get_tickers()
        balance = get_balances()
        balances = {}
        balances["BTC"] = 0
        balances["USDT"] = 0
        #print(balance)
        USDT_total = 0
        print("------------- OUR WALLET -------------")
        for coin in balance:
            if balance[coin] > 0:
                if coin == "USDT":
                    print("USDT = "+str(balance[coin]))
                    USDT_total += balance[coin]
                else:
                    coinSymbolUSDT = coin+"/USDT"
                    USDT_value = tickers[coinSymbolUSDT]["bid"]*balance[coin]
                    USDT_total += USDT_value
                    print(coin+" ("+str(balance[coin])+") USDT value = "+str(USDT_value))
     
        #print("Wallet value in USDT = "+str(USDT_total))
        '''
        for key,amount in c_portfolio.items():
            print(key+"==>"+str(amount))
            coinSymbolUSDT = key+"/USDT"
            coinValue = 0
            if coinSymbolUSDT in tickers:
                coinValue = tickers[coinSymbolUSDT]["bid"]*amount
                balances["USDT"] += coinValue
            print(key+" value in USDT = "+str(coinValue))
        '''
        print("Wallet value in USDT = "+str(USDT_total))
        log_file.write("\n Wallet value in USDT = "+str(USDT_total))

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