# crypto-bots
Python experimentations around automatic cryptocurrencies trading.

## What it does
It doesn't look for opportunities. Instead, it reads a JSON of opportunities and passes sell / buy orders depending on our current portfolio and trading platforms avaibilities.

## Improvements
* Find a better source of opportunities
* Error handling : crashes are serious sources of loss resulting of missed sell orders
* Making it async