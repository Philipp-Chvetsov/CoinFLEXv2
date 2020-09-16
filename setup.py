# Credentials
ENV = 'STAGE'


class Env:
    if ENV == 'STAGE':
        ws_url = 'wss://v2stgapi.coinflex.com/v2/websocket'
        rest_url = 'https://v2stgapi.coinflex.com'
        rest_short = 'v2stgapi.coinflex.com'
        # Change api_key and api_secret to your public and secret keys respectively.
        api_key = ''
        api_secret = ''

    elif ENV == 'LIVE':
        ws_url = 'wss://v2api.coinflex.com/v2/websocket'
        rest_url = 'https://v2api.coinflex.com'
        rest_short = 'v2api.coinflex.com'
        # Change api_key and api_secret to your public and secret keys respectively.
        api_key = ''
        api_secret = ''


class BVars:
    market = "BTC-USD-SWAP-LIN"  # Change markets here
    cf_markets = {
        "op": "subscribe",
        "args": ["futures/depth:" + market, "order:" + market],  # "position:all" , "balances:all"],
        "tag": "1",
    }
    bin_url = "wss://dstream.binance.com/ws"
    bin_markets = {"method": "SUBSCRIBE", "params": ["btcusd_perp@bookTicker"], "id": 1}
    cf_bid, cf_bidq, cf_ask, cf_askq = 0, 0, 0, 0
    mid = 0
    BIN_WS_FLAG, CF_WS_FLAG = False, False
    BID_QUOTING_FLAG, ASK_QUOTING_FLAG = False, False
    FLATTEN_FLAG, FLATTEN_MOD_FLAG = False, False
    BIN_FIRST_RUN_FLAG = True
    og_size, bid_size, ask_size = 1, 1, 1  # Number of BTC, og_size = original size
    max_position = 100     # BTC
    working_position = 0   # BTC
    spread = 5 / 10_000    # Basis points from "fair value" 1 basis point = 0.01%
    cf_balance = 0         # USDC balance
    working_bid, working_bidq, working_ask, working_askq = 0, 0, 0, 0
    order_ids = ["1", "2", "3", "4"]  # Bid, Ask, Ask, Bid
    bid_id, ask_id = 0, 0
    flatten_id, flatten_p, flatten_q = 0, 0, 0
    rate_limit = 200
    logger = ''
