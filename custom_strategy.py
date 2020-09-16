import asyncio
import json
import sys
import traceback
import websockets
import coinflexREST as cfRest
import coinflexWS as cfWS
from setup import Env, BVars

global logger


async def coinflex():
    # Connect to CoinFLEX's websocket and subscribe to the orderbook, order and position channels.
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

            # This is where the trading logic starts.
            while True:
                try:
                    # Await a message from CoinFLEX's websocket.
                    response = await ws.recv()
                    msg = json.loads(response)
                    # Output the message from CoinFLEX's websocket.
                    BVars.logger.info(str(msg))

                except Exception as err:
                    traceback.print_exc(file=sys.stdout)
                    BVars.logger.info("error: CF WS loop failed " + repr(err))
                    await ws.close()


async def subscribe():
    global logger
    tasks = [
        coinflex(),
    ]
    # Start the bot.
    BVars.logger.info('--- Bot Starting Up ---')
    await asyncio.wait(tasks)


def main():
    # Start the co-routines.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(subscribe())


if __name__ == "__main__":
    # setup the logger.
    BVars.logger = cfWS.setup_logger()

    # enter the main function.
    main()
