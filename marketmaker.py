import asyncio
import json
import math
import sys
import time
import traceback
import websockets
import coinflexREST as cfRest
import coinflexWS as cfWS
from setup import Env, BVars

global bin_ws, ws, logger


async def cf_sub():
    global ws, bin_ws
    # Connect to CoinFLEX's websocket and subscribe to the orderbook, order and position channels.
    max_pos_timer = time.time()
    while True:
        async with websockets.connect(Env.ws_url) as ws:
            # Authenticate the websocket connection.
            await ws.send(json.dumps(await cfWS.auth(Env.api_key, Env.api_secret)))

            # Connect to the orderbook, order, and position channels.
            await ws.send(json.dumps(BVars.cf_markets))

            login, markets, orders = False, False, False
            setup = False

            # Ensure all of the channels have been connected to prior to trading.
            while not setup:
                try:
                    response = await ws.recv()
                    msg = json.loads(response)
                    BVars.logger.info("setup " + str(msg))
                    if "event" in msg and "success" in msg:
                        if msg["event"] == "login" and msg["success"]:
                            login = True
                    if "channel" in msg:
                        if (
                            msg["channel"] == "futures/depth:" + BVars.market
                            and msg["event"] == "subscribe"
                        ):
                            markets = True
                        if (
                            msg["channel"] == "order:" + BVars.market
                            and msg["event"] == "subscribe"
                        ):
                            orders = True
                        if (
                            msg["channel"] == "position:" + BVars.market
                            and msg["event"] == "subscribe"
                        ):
                            positions = True
                    if login and markets and orders:
                        setup = True
                except Exception as error:
                    BVars.logger.info("setup caught this error: " + repr(error))

            BVars.logger.info("successfully connected to CoinFLEX")

            i = 1
            while ws.open:
                await asyncio.sleep(3)
                # If reconnecting to Binance's websocket fails for over a minute (e.g. maintenance), kill the bot.
                if i > 20:
                    BVars.logger.info("Halting Trading: Restarting Derp BLP")
                    exit()
                    # Use os.execv(__file__, sys.argv) if you would like to restart the bot completely instead.
                i += 1

                # This is where the trading logic starts.
                while BVars.BIN_WS_FLAG:
                    i = 1
                    try:
                        # Await a message from CoinFLEX's websocket.
                        response = await ws.recv()
                        msg = json.loads(response)

                        # Catch orders that may be cancelled by CancelAll.
                        if "data" in msg and "table" in msg:
                            if msg["table"] == "order":
                                new_msg = msg["data"][0]
                                BVars.logger.info("new_msg" + str(new_msg))
                                if (
                                    new_msg["notice"] == "OrderClosed"
                                    and new_msg["status"] == "CANCELED_BY_USER"
                                ):
                                    if (
                                        new_msg["side"] == "BUY"
                                        and new_msg["clientOrderId"] == BVars.order_ids[0]
                                    ):
                                        BVars.BID_QUOTING_FLAG = False
                                        BVars.bid_id, BVars.working_bid, BVars.working_bidq = (
                                            0,
                                            0,
                                            0,
                                        )
                                        continue
                                    elif (
                                        new_msg["side"] == "SELL"
                                        and new_msg["clientOrderId"] == BVars.order_ids[1]
                                    ):
                                        BVars.ASK_QUOTING_FLAG = False
                                        BVars.ask_id, BVars.working_ask, BVars.working_askq = (
                                            0,
                                            0,
                                            0,
                                        )
                                        continue
                                    elif (
                                        new_msg["clientOrderId"] == BVars.order_ids[2]
                                        or new_msg["clientOrderId"] == BVars.order_ids[3]
                                    ):
                                        BVars.FLATTEN_FLAG = False
                                        BVars.FLATTEN_MOD_FLAG = False
                                        BVars.flatten_p, BVars.flatten_q, BVars.flatten_id = (
                                            0,
                                            0,
                                            0,
                                        )
                                        continue

                        # Parse new orderbook data and check for an OrderMatched message.
                        if "data" in msg:
                            msg = msg["data"][0]
                            # Track CoinFLEX prices and check for position changes
                            skip = await cfWS.parse_message(BVars, ws, msg, mgmt=False)
                            if skip:
                                continue

                        # Ensure that position size isn't growing too large for your personal risk tolerance ;).
                        if (
                            abs(BVars.working_position) >= BVars.max_position
                            and time.time() > max_pos_timer + 30
                        ):
                            BVars.logger.info("Max Position Reached")
                            max_pos_timer = time.time()

                        # Update active bids if the fair value of the contract has changed by 2 basis points.
                        if (
                            BVars.BID_QUOTING_FLAG
                            and BVars.working_position < BVars.max_position
                        ):
                            if (
                                BVars.mid * (1 - BVars.spread + 0.0002)
                                <= BVars.working_bid
                                or BVars.mid * (1 - BVars.spread - 0.0002)
                                >= BVars.working_bid
                                or BVars.working_bidq < BVars.bid_size * 0.5
                            ):
                                # Calculate the new bid_price to use then cancel and replace the working order.
                                bid_price = (
                                    math.floor(BVars.mid * (1 - BVars.spread) * 2) / 2
                                )
                                await cfWS.CancelOrder(
                                    BVars, ws, BVars.bid_id, BVars.market
                                )
                                await cfWS.PlaceOrder(
                                    BVars,
                                    ws,
                                    BVars.order_ids[0],
                                    BVars.market,
                                    "BUY",
                                    "LIMIT",
                                    BVars.bid_size,
                                    "MAKER_ONLY_REPRICE",
                                    bid_price,
                                )
                                # cfModifyOrder(BVars, ws, BVars.bid_id, BVars.market, "BUY", BVars.bid_size, bid_price)

                        # Update active asks if the fair value of the contract has changed by 2 basis points.
                        if (
                            BVars.ASK_QUOTING_FLAG
                            and BVars.working_position > -BVars.max_position
                        ):
                            if (
                                BVars.mid * (1 + BVars.spread + 0.0002)
                                <= BVars.working_ask
                                or BVars.mid * (1 + BVars.spread - 0.0002)
                                >= BVars.working_ask
                                or BVars.working_askq < BVars.ask_size * 0.5
                            ):
                                # Calculate the new ask_price to use then cancel and replace the working order.
                                ask_price = (
                                    math.ceil(BVars.mid * (1 + BVars.spread) * 2) / 2
                                )
                                await cfWS.CancelOrder(
                                    BVars, ws, BVars.ask_id, BVars.market
                                )
                                await cfWS.PlaceOrder(
                                    BVars,
                                    ws,
                                    BVars.order_ids[1],
                                    BVars.market,
                                    "SELL",
                                    "LIMIT",
                                    BVars.ask_size,
                                    "MAKER_ONLY_REPRICE",
                                    ask_price,
                                )
                                # await cfModifyOrder(BVars, ws, BVars.ask_id, BVars.market, "SELL", BVars.ask_size, ask_price)

                        # Place orders if there are no working orders.
                        if not BVars.BIN_FIRST_RUN_FLAG:
                            if (
                                not BVars.BID_QUOTING_FLAG
                                and BVars.working_position < BVars.max_position
                            ):
                                # Calculate the bid_price to use then place an order.
                                bid_price = (
                                    math.floor(BVars.mid * (1 - BVars.spread) * 2) / 2
                                )
                                await cfWS.PlaceOrder(
                                    BVars,
                                    ws,
                                    BVars.order_ids[0],
                                    BVars.market,
                                    "BUY",
                                    "LIMIT",
                                    BVars.bid_size,
                                    "MAKER_ONLY_REPRICE",
                                    bid_price,
                                )

                            if (
                                not BVars.ASK_QUOTING_FLAG
                                and BVars.working_position > -BVars.max_position
                            ):
                                # Calculate the ask_price to use then place an order.
                                ask_price = (
                                    round(BVars.mid * (1 + BVars.spread) * 2) / 2
                                )
                                await cfWS.PlaceOrder(
                                    BVars,
                                    ws,
                                    BVars.order_ids[1],
                                    BVars.market,
                                    "SELL",
                                    "LIMIT",
                                    BVars.ask_size,
                                    "MAKER_ONLY_REPRICE",
                                    ask_price,
                                )

                    except Exception as err:
                        traceback.print_exc(file=sys.stdout)
                        BVars.logger.info("error: CF WS loop failed " + repr(err))
                        await ws.close()

                # Binance's websocket has disconnected, cancel all working orders and wait to reconnect.
                if (
                    not bin_ws.open
                    and (BVars.bid_id != 0 or BVars.ask_id != 0 or BVars.flatten_id != 0)
                ):
                    cfRest.cancelAll(111, Env.rest_short, Env.rest_url, Env.api_key, Env.api_secret)
                    BVars.working_bid, BVars.working_bidq, BVars.bid_id = 0, 0, 0
                    BVars.working_ask, BVars.working_askq, BVars.ask_id = 0, 0, 0
                    BVars.flatten_p, BVars.flatten_q, BVars.flatten_id = 0, 0, 0
                    BVars.BID_QUOTING_FLAG, BVars.ASK_QUOTING_FLAG, BVars.FLATTEN_FLAG = (
                        False,
                        False,
                        False,
                    )
                    await asyncio.sleep(10)

            # CoinFLEX's websocket has disconnected, cancel all working orders and attempt to reconnect.
            cfRest.cancelAll(111, Env.rest_short, Env.rest_url, Env.api_key, Env.api_secret)
            await asyncio.sleep(5)
            BVars.working_bid, BVars.working_bidq, BVars.bid_id = 0, 0, 0
            BVars.working_ask, BVars.working_askq, BVars.ask_id = 0, 0, 0
            BVars.flatten_p, BVars.flatten_q, BVars.flatten_id = 0, 0, 0
            BVars.BID_QUOTING_FLAG, BVars.ASK_QUOTING_FLAG, BVars.FLATTEN_FLAG = (
                False,
                False,
                False,
            )
            BVars.logger.info("error: CF WS disconnected, reconnecting")


async def bin_sub():
    global bin_ws
    while True:
        async with websockets.connect(BVars.bin_url) as bin_ws:
            # Connect to Binance's websocket and subscribe to the coin-margined channels.
            await bin_ws.send(json.dumps(BVars.bin_markets))
            BVars.BIN_WS_FLAG = True
            BVars.logger.info("successfully connected to Binance")
            while bin_ws.open and BVars.BIN_WS_FLAG:

                try:
                    # Await a message from Binance's websocket.
                    response = await bin_ws.recv()
                    msg = json.loads(response)
                    # Uncomment the next line to log Binance price data.
                    # BVars.logger.info(msg)
                    if "b" in msg and "a" in msg:
                        BVars.bin_bid = float(msg["b"])   # Bid price
                        BVars.bin_bidq = float(msg["B"])  # Bid size in 100's of USD
                        BVars.bin_ask = float(msg["a"])   # Ask price
                        BVars.bin_askq = float(msg["A"])  # Ask size in 100's of USD

                        # Establish a mid price for Binance's market
                        BVars.mid = (BVars.bin_bid + BVars.bin_ask) / 2.0
                        BVars.BIN_FIRST_RUN_FLAG = False

                except Exception as error:
                    traceback.print_exc(file=sys.stdout)
                    BVars.logger.info("error: Binance WS loop failed " + repr(error))
                    BVars.BIN_WS_FLAG = False
                    BVars.BIN_FIRST_RUN_FLAG = True

            await asyncio.sleep(3)
            BVars.BIN_WS_FLAG = False
            BVars.BIN_FIRST_RUN_FLAG = True
            BVars.logger.info("error: Binance WS disconnected, reconnecting")


async def subscribe_all():
    global logger

    # Initialise the tasks, bin_sub is to stream price data from binance
    # and cf_sub is to stream price data from coinflex and place orders.
    tasks = [
        bin_sub(),
        cf_sub(),
    ]
    
    # Start the bot.
    BVars.logger.info('--- Starting Up Market Making Bot ---')
    await asyncio.wait(tasks)


def main():
    # Initialise the BTC-USD-SWAP-LIN (BVars.market) position using a rest call.
    positions = cfRest.getPositions(123, Env.rest_short, Env.rest_url, Env.api_key, Env.api_secret)["data"]
    if positions is not None:
        for i in positions:
            BVars.logger.info(str(i))
            if i["instrumentId"] == BVars.market:
                BVars.working_position = round(float(i["quantity"]), 3)
                break

    # Initialise USD balance using a rest call.
    balance = cfRest.getBalances(456, Env.rest_short, Env.rest_url, Env.api_key, Env.api_secret)["data"]
    if balance is not None:
        for i in balance:
            if i["instrumentId"] == "USD":
                BVars.cf_balance = round(float(i["available"]), 4)
                break

    # Initialise any working orders that belong to this bot.
    orders = cfRest.getOrders(789, Env.rest_short, Env.rest_url, Env.api_key, Env.api_secret)["data"]
    if orders:
        for i in orders:
            if i["clientOrderId"] == BVars.order_ids[0]:
                BVars.working_bid = float(i["price"])
                BVars.working_bidq = float(i["quantity"])
                BVars.bid_id = str(i["orderId"])
                BVars.BID_QUOTING_FLAG = True
                continue
            if i["clientOrderId"] == BVars.order_ids[1]:
                BVars.working_ask = float(i["price"])
                BVars.working_askq = float(i["quantity"])
                BVars.ask_id = str(i["orderId"])
                BVars.ASK_QUOTING_FLAG = True
                continue
            if (
                i["clientOrderId"] == BVars.order_ids[2]
                or i["clientOrderId"] == BVars.order_ids[3]
            ):
                BVars.flatten_p = float(i["price"])
                BVars.flatten_q = float(i["quantity"])
                BVars.flatten_id = str(i["orderId"])
                BVars.FLATTEN_FLAG = True

    loop = asyncio.get_event_loop()
    loop.run_until_complete(subscribe_all())


if __name__ == "__main__":
    # setup the logger.
    BVars.logger = cfWS.setup_logger()
    
    # enter the main function.
    main()
