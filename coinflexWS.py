import base64
import hashlib
import hmac
import json
import logging
import math
import time
import traceback
import random
import sys


def setup_logger():
    # add logging.StreamHandler() to handlers list if needed
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # create file handler which logs even debug messages
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s, %(message)s')
    handler.setFormatter(formatter)

    # add the handlers to logger
    logger.addHandler(handler)
    return logger


async def auth(api_key, api_secret):
    timestamp = str(int(time.time() * 1_000))
    message = bytes(timestamp + "GET" + "/auth/self/verify", "utf-8")
    secret = bytes(api_secret, "utf-8")
    signature = base64.b64encode(
        hmac.new(secret, message, digestmod=hashlib.sha256).digest()
    ).decode("utf-8")
    args = {"apiKey": api_key, "timestamp": timestamp, "signature": signature}
    return {"op": "login", "data": args, "tag": 1}


async def ModifyOrder(BVars, ws, oid, market, side, qty, price, tag=20):
    purpose = "modifyorder"
    BVars.logger.info("modifying " + str(side) + " order to " + str(price) + str(qty))
    await ws.send(
        json.dumps(
            {
                "op": "modifyorder",
                "data": {
                    "marketCode": str(market),
                    "orderId": int(oid),
                    "side": str(side),
                    "price": price,
                    "quantity": qty,
                },
                "tag": tag,
            }
        )
    )
    await OrderMgmt(BVars, ws, purpose)
    return


async def PlaceOrder(BVars, ws, oid, market, side, o_type, qty, tif, price, tag=10):
    purpose = "placeorder"
    BVars.logger.info("placing " + str(side) + " order at " + str(price) + " with size " + str(qty))
    await ws.send(
        json.dumps(
            {
                "op": "placeorder",
                "data": {
                    "clientOrderId": int(oid),
                    "marketCode": str(market),
                    "side": str(side),
                    "orderType": str(o_type),
                    "quantity": qty,
                    "timeInForce": str(tif),
                    "price": price,
                },
                "tag": tag,
            }
        )
    )
    await OrderMgmt(BVars, ws, purpose)
    return


async def CancelOrder(BVars, ws, oid, market):
    purpose = "cancelorder"
    BVars.logger.info("cancelling orderId: " + str(oid))
    await ws.send(
        json.dumps(
            {"op": "cancelorder", "data": {"marketCode": market, "orderId": str(oid)}}
        )
    )
    await OrderMgmt(BVars, ws, purpose)
    return


async def OrderMgmt(BVars, ws, purpose):
    can_exit = False
    order_ids = BVars.order_ids
    while ws.open and not can_exit:
        try:
            # Await a websocket message from CoinFLEX.
            response = await ws.recv()
            msg = json.loads(response)
            print('MGMT', msg)
            # Parse new orderbook data and check for an OrderMatched message.
            if "data" in msg and 'submitted' not in msg:
                new_msg = msg["data"][0]
                skip = await parse_message(BVars, ws, new_msg, mgmt=True)
                if skip:
                    continue

            # Register new order IDs, prices, and quantities.
            if "data" in msg and "table" in msg:
                if msg["table"] == "order":
                    msg = msg["data"][0]
                    BVars.logger.info("MGMT " + str(msg))
                    if (
                        "clientOrderId" in msg
                        and msg["status"] == "OPEN"
                        and (
                            msg["notice"] == "OrderOpened"
                            or msg["notice"] == "OrderModified"
                        )
                    ):
                        # Update bid information.
                        if (
                            msg["clientOrderId"] == order_ids[0]
                            and msg["side"] == "BUY"
                        ):
                            BVars.working_bid = float(msg["price"])
                            BVars.working_bidq = float(msg["quantity"])
                            BVars.bid_id = str(msg["orderId"])
                            BVars.BID_QUOTING_FLAG = True
                            if purpose == "placeorder" or purpose == "modifyorder":
                                can_exit = True
                            continue

                        # Update ask information.
                        if (
                            msg["clientOrderId"] == order_ids[1]
                            and msg["side"] == "SELL"
                        ):  # generalise the ID
                            BVars.working_ask = float(msg["price"])
                            BVars.working_askq = float(msg["quantity"])
                            BVars.ask_id = str(msg["orderId"])
                            BVars.ASK_QUOTING_FLAG = True
                            if purpose == "placeorder" or purpose == "modifyorder":
                                can_exit = True
                            continue

                        # Update position flattening order information.
                        if (
                            msg["clientOrderId"] == order_ids[2]
                            and msg["side"] == "SELL"
                        ):  # generalise the ID
                            BVars.flatten_p = float(msg["price"])
                            BVars.flatten_q = float(msg["quantity"])
                            BVars.flatten_id = str(msg["orderId"])
                            BVars.FLATTEN_FLAG = True
                            BVars.FLATTEN_MOD_FLAG = False
                            if purpose == "placeorder" or purpose == "modifyorder":
                                can_exit = True
                            continue

                        # Update position flattening order information.
                        if (
                            msg["clientOrderId"] == order_ids[3]
                            and msg["side"] == "BUY"
                        ):  # generalise the ID
                            BVars.flatten_p = float(msg["price"])
                            BVars.flatten_q = float(msg["quantity"])
                            BVars.flatten_id = str(msg["orderId"])
                            BVars.FLATTEN_MOD_FLAG = False
                            BVars.FLATTEN_FLAG = True
                            if purpose == "placeorder" or purpose == "modifyorder":
                                can_exit = True
                            continue

                    # Remove cancelled orders from the internal order tracking system.
                    if (
                        msg["notice"] == "OrderClosed"
                        and msg["status"] == "CANCELED_BY_USER"
                    ):
                        if (
                            msg["side"] == "BUY"
                            and msg["clientOrderId"] == order_ids[0]
                        ):
                            BVars.BID_QUOTING_FLAG = False
                            BVars.bid_id, BVars.working_bid, BVars.working_bidq = 0, 0, 0
                            if purpose == "cancelorder":
                                can_exit = True
                            continue
                        elif (
                            msg["side"] == "SELL"
                            and msg["clientOrderId"] == order_ids[1]
                        ):
                            BVars.ASK_QUOTING_FLAG = False
                            BVars.ask_id, BVars.working_ask, BVars.working_askq = 0, 0, 0
                            if purpose == "cancelorder":
                                can_exit = True
                            continue
                        elif (
                            msg["clientOrderId"] == order_ids[3]
                            or msg["clientOrderId"] == order_ids[2]
                        ):
                            BVars.FLATTEN_FLAG = False
                            BVars.FLATTEN_MOD_FLAG = False
                            BVars.flatten_p, BVars.flatten_q, BVars.flatten_id = 0, 0, 0
                            if purpose == "cancelorder":
                                can_exit = True
                            continue

                    if msg["status"] == "REJECT_AMEND_ORDER_ID_NOT_FOUND":
                        BVars.logger.info("AMENDMENT REJECTED " + str(msg))
                        if purpose == "modifyorder":
                            can_exit = True
                        continue

            if "table" not in msg:
                if "submitted" in msg:
                    BVars.logger.info(str(msg))
                    if msg["submitted"] is False:
                        if msg["event"] == "cancelorder" or msg["event"] == "CANCEL":
                            # The order was filled before the cancelOrder went through.
                            if purpose == "cancelorder":
                                can_exit = True
                            continue

                        if msg["tag"] == order_ids[2] or msg["tag"] == order_ids[3]:
                            if purpose == "placeorder" or purpose == "modifyorder":
                                can_exit = True
                            if msg["event"] == "placeorder":
                                BVars.FLATTEN_FLAG = False
                            if msg["event"] == "modifyorder":
                                BVars.FLATTEN_MOD_FLAG = False

                if "success" in msg:
                    BVars.logger.info(str(msg))
                    if purpose == "placeorder" or purpose == "modifyorder":
                        can_exit = True
                    if msg["tag"] == order_ids[2] or msg["tag"] == order_ids[3]:
                        if msg["event"] == "placeorder":
                            BVars.FLATTEN_FLAG = False
                        if msg["event"] == "modifyorder":
                            BVars.FLATTEN_MOD_FLAG = False
                    BVars.logger.info(
                        "error: " + str(msg["event"]) + " submission failed"
                    )

        except Exception as err:
            traceback.print_exc(file=sys.stdout)
            BVars.logger.info("error: CF order management loop failed: " + repr(err))
            exit()
    return


async def OrderMatched(BVars, msg):
    if msg["clientOrderId"] not in BVars.order_ids:
        return
    BVars.logger.info(str(msg))
    match = float(msg["matchQuantity"])
    remain = round(float(msg["remainQuantity"]), 3)

    # If the OrderMatched was a partial fill update the order tracking and position information accordingly.
    if remain > 0 and (
        msg["clientOrderId"] == BVars.order_ids[0]
        or msg["clientOrderId"] == BVars.order_ids[1]
    ):
        if msg["side"] == "BUY":
            BVars.working_bid = remain
            BVars.working_position = round(BVars.working_position + match, 3)
        else:
            BVars.working_ask = remain
            BVars.working_position = round(BVars.working_position - match, 3)

    # If the OrderMatched was a fill then reset the order tracking entirely and update position information accordingly.
    if remain == 0 and (
        msg["clientOrderId"] == BVars.order_ids[0]
        or msg["clientOrderId"] == BVars.order_ids[1]
    ):
        if msg["side"] == "BUY":
            BVars.BID_QUOTING_FLAG = False
            BVars.bid_id, BVars.working_bid, BVars.working_bidq = 0, 0, 0
            BVars.working_position = round(BVars.working_position + match, 3)
        else:
            BVars.ASK_QUOTING_FLAG = False
            BVars.ask_id, BVars.working_ask, BVars.working_askq = 0, 0, 0
            BVars.working_position = round(BVars.working_position - match, 3)

    # If the OrderMatched was a risk reducing (flattening) match then update the flattening tracking as needed.
    if msg["clientOrderId"] == BVars.order_ids[2] or msg["clientOrderId"] == BVars.order_ids[3]:
        if remain == 0:
            BVars.flatten_q, BVars.flatten_p, BVars.flatten_id = 0, 0, 0
            BVars.FLATTEN_FLAG = False
            if msg["side"] == "BUY":
                BVars.working_position = round(BVars.working_position + match, 3)
            else:
                BVars.working_position = round(BVars.working_position - match, 3)

        if remain > 0:
            BVars.flatten_q = remain
            if msg["side"] == "BUY":
                BVars.working_position = round(BVars.working_position + match, 3)
            else:
                BVars.working_position = round(BVars.working_position - match, 3)

    # Update order sizes in case the bot is approaching max_position
    BVars.logger.info("filled: " + str(BVars.working_position))
    if BVars.working_position > BVars.max_position - BVars.bid_size:
        BVars.bid_size = BVars.max_position - BVars.working_position
        BVars.logger.info("position is approaching max: " + str(BVars.working_position))
    if BVars.working_position < -BVars.max_position + BVars.ask_size:
        BVars.ask_size = BVars.working_position + BVars.max_position
        BVars.logger.info("position is approaching max: " + str(BVars.working_position))
    if abs(BVars.working_position) < BVars.max_position:
        BVars.bid_size = BVars.og_size
        BVars.ask_size = BVars.og_size
    return


async def parse_message(BVars, ws, msg, mgmt=True):
    if "asks" in msg and "bids" in msg:
        if msg["asks"] == [] or msg["bids"] == []:
            return True
        BVars.cf_bid = msg["bids"][0][0]
        BVars.cf_bidq = msg["bids"][0][1]
        BVars.cf_ask = msg["asks"][0][0]
        BVars.cf_askq = msg["asks"][0][1]

        # Place risk reducing (flattening) orders if the bot has a non-zero position.
        if (
            BVars.cf_ask - BVars.cf_bid <= 3.0
            and abs(BVars.working_position) >= 0.001
            and not mgmt
        ):
            await flatten_position(BVars, ws)

    # Process OrderMatched messages to keep track of position and order fills.
    if "notice" in msg:
        if msg["notice"] == "OrderMatched" and "matchQuantity" in msg:
            await OrderMatched(BVars, msg)
            return True
    return False


async def flatten_position(BVars, ws):
    abs_work_pos = abs(BVars.working_position)

    # Randomise flattening size to make the bot's activity less obvious to other market participants.
    if abs_work_pos > 1:
        qty = round(random.randint(1_000, round(abs_work_pos * 1_000)) / 1_000, 3)
    else:
        qty = abs_work_pos

    # Place the risk reducing order at the mid price
    if BVars.working_position >= 0.001 and not BVars.FLATTEN_FLAG:
        BVars.logger.info(
            "flattening position " + str(BVars.working_position)
        )
        BVars.FLATTEN_FLAG = True
        await PlaceOrder(
            BVars,
            ws,
            BVars.order_ids[2],
            BVars.market,
            "SELL",
            "LIMIT",
            qty,
            "MAKER_ONLY_REPRICE",
            math.ceil(BVars.mid * 2) / 2.0,
            tag=BVars.order_ids[2],
        )

    if BVars.working_position <= -0.001 and not BVars.FLATTEN_FLAG:
        BVars.logger.info(
            "flattening position " + str(BVars.working_position)
        )
        BVars.FLATTEN_FLAG = True
        await PlaceOrder(
            BVars,
            ws,
            BVars.order_ids[3],
            BVars.market,
            "BUY",
            "LIMIT",
            qty,
            "MAKER_ONLY_REPRICE",
            math.floor(BVars.mid * 2) / 2.0,
            tag=BVars.order_ids[3],
        )

    # If the fair price has moved more than 1 basis point from the flatten_p then update the risk reducing order
    # but if flatten_p is the best bid or ask price, then take no action.
    if BVars.flatten_p > BVars.mid * 1.0001 or BVars.flatten_p < BVars.mid * 0.9999:
        BVars.FLATTEN_FLAG = False
        BVars.FLATTEN_MOD_FLAG = False
        if (BVars.flatten_p == BVars.cf_bid and BVars.mid > BVars.cf_bid) or \
           (BVars.flatten_p == BVars.cf_ask and BVars.mid < BVars.cf_ask):

            BVars.FLATTEN_FLAG = True
            BVars.FLATTEN_MOD_FLAG = True

    if BVars.working_position > 0 and not BVars.FLATTEN_FLAG and not BVars.FLATTEN_MOD_FLAG:
        BVars.FLATTEN_FLAG = True
        BVars.FLATTEN_MOD_FLAG = True
        await CancelOrder(BVars, ws, BVars.flatten_id, BVars.market)
        await PlaceOrder(
            BVars,
            ws,
            BVars.order_ids[2],
            BVars.market,
            "SELL",
            "LIMIT",
            qty,
            "MAKER_ONLY_REPRICE",
            math.ceil(BVars.mid * 2) / 2.0,
            tag=BVars.order_ids[2],
        )
        # await cfModifyOrder(BVars, ws, BVars.flatten_id, BVars.market, "SELL", qty,
        #                    round(BVars.mid * 2) / 2.0, tag=30)

    if BVars.working_position < 0 and not BVars.FLATTEN_FLAG and not BVars.FLATTEN_MOD_FLAG:
        BVars.FLATTEN_FLAG = True
        BVars.FLATTEN_MOD_FLAG = True
        await CancelOrder(BVars, ws, BVars.flatten_id, BVars.market)
        await PlaceOrder(
            BVars,
            ws,
            BVars.order_ids[3],
            BVars.market,
            "BUY",
            "LIMIT",
            qty,
            "MAKER_ONLY_REPRICE",
            math.floor(BVars.mid * 2) / 2.0,
            tag=BVars.order_ids[3],
        )
        # await cfModifyOrder(BVars, ws, BVars.flatten_id, BVars.market, "BUY", qty,
        #                    round(BVars.mid * 2) / 2.0, tag=40)
    return
