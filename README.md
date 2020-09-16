# CoinFLEX v2
CoinFLEX V2 API modules, which can be used as a template or guideline to create bots or collect data.

This is a sample market making bot to be used on CoinFLEX, it's free to use and edit as you wish for your own trading needs. 

This repository contains:

1\ A module to work with CoinFLEX's REST and Websocket APIs.
2\ Market data is streamed via Websocket.
3\ Orders are tracked and may be canceled/placed/modified via the Websocket API module, additionally, orders can be queried by the REST module.
4\ Connectivity is important, and so a strategy to cancel all working orders and reconnect has been implemented
5\ custom_strategy.py is a barebones framework that can be used to build out a functional bot. 
6\ marketmaker.py is a simple strategy that queries Binance's coin-margined perpetuals to provide a 'fair value'. A single bid and ask is placed and managed around the current 'fair value'. This implementation does NOT hedge. 
7\ With this guideline you should be able to build something more interesting, you could try to arb CoinFLEX's SPOT, PERP and REPO markets, perform funding arbitrage between CoinFLEX and other exchanges, build directional trend-following/mean-reversion strategies that are executed algorithmically, the possibilities are truly endless.

Develop on Stage first (https://v2stg.coinflex.com/) your account will be preloaded with mock capital to test with, not all of us can be Andre Cronje ;).

Myself, and CoinFLEX are not responsible for any losses incurred when using this code. This code is intended for sample purposes ONLY - do not use this code for real trades unless you fully understand what it does and what its caveats are.

These bots will likely lose you money, they are intended to show the basics of market-making, outline a potential trading algo structure, and provide examples of how to interact with CoinFLEX's Rest and WebSocket endpoints.

# compatibility 
This module supports Python 3.5 and later.
