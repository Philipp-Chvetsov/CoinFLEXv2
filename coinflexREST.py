import requests
import hmac
import base64
import hashlib
import datetime


def getPositions(nonce, rest_short, rest_url, api_key, api_secret):
    ts = str(datetime.datetime.utcnow().isoformat())[:19]
    query_string = ts + '\n' + str(nonce) + '\n' + 'GET' + '\n' + rest_short + '\n' + '/v2/positions' + '\n'
    sig = base64.b64encode(
        hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
    header = {'Content-Type': 'application/json', 'AccessKey': api_key,
              'Timestamp': ts, 'Signature': sig, 'Nonce': str(nonce)}
    resp = requests.get(rest_url + "/v2/positions", headers=header).json()
    print(resp)
    return resp


def getBalances(nonce, rest_short, rest_url, api_key, api_secret):
    ts = str(datetime.datetime.utcnow().isoformat())[:19]
    query_string = ts + '\n' + str(nonce) + '\n' + 'GET' + '\n' + rest_short + '\n' + '/v2/balances' + '\n'
    sig = base64.b64encode(
        hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
    header = {'Content-Type': 'application/json', 'AccessKey': api_key,
              'Timestamp': ts, 'Signature': sig, 'Nonce': str(nonce)}
    resp = requests.get(rest_url + "/v2/balances", headers=header).json()
    print(resp)
    return resp


def getOrders(nonce, rest_short, rest_url, api_key, api_secret):
    ts = str(datetime.datetime.utcnow().isoformat())[:19]
    query_string = ts + '\n' + str(nonce) + '\n' + 'GET' + '\n' + rest_short + '\n' + '/v2/orders' + '\n'
    sig = base64.b64encode(
        hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
    header = {'Content-Type': 'application/json', 'AccessKey': api_key,
              'Timestamp': ts, 'Signature': sig, 'Nonce': str(nonce)}
    resp = requests.get(rest_url + "/v2/orders", headers=header).json()
    print(resp)
    return resp


def getTrades(nonce, rest_short, rest_url, api_key, api_secret):
    ts = str(datetime.datetime.utcnow().isoformat())[:19]
    query_string = ts + '\n' + str(nonce) + '\n' + 'GET' + '\n' + rest_short + '\n' + '/v2/trades/BTC-USD-SWAP-LIN' + '\n'
    sig = base64.b64encode(
        hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
    header = {'Content-Type': 'application/json', 'AccessKey': api_key,
              'Timestamp': ts, 'Signature': sig, 'Nonce': str(nonce)}
    resp = requests.get(rest_url + "/v2/trades/BTC-USD-SWAP-LIN", headers=header).json()
    print(resp)
    return resp


def cancelAll(nonce, rest_short, rest_url, api_key, api_secret):
    ts = str(datetime.datetime.utcnow().isoformat())[:19]
    query_string = ts + '\n' + str(nonce) + '\n' + 'DELETE' + '\n' + rest_short + '\n' + '/v2/cancel/orders' + '\n'
    sig = base64.b64encode(
        hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
    header = {'Content-Type': 'application/json', 'AccessKey': api_key,
              'Timestamp': ts, 'Signature': sig, 'Nonce': str(nonce)}
    resp = requests.delete(rest_url + '/v2/cancel/orders', headers=header).json()
    print(resp)
    return resp
