import time

from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws
from datetime import datetime, timedelta, date
from  time import sleep
import os
import pyotp
import requests
import json
import math
import pytz
from urllib.parse import parse_qs,urlparse
import warnings
import pandas as pd
import base64

BROKER_APP  = None
BROKER_SOCKET  = None
access_token = None
client_id = None
ltp = {}

def getEncodedString(string):
    string = str(string)
    base64_bytes = base64.b64encode(string.encode("ascii"))
    return base64_bytes.decode("ascii")




def login():
    global BROKER_APP
    global access_token
    global client_id

    redirect_uri = 'https://0.0.0.0:8080/'
    client_id='IC8PF0KRVY-100'
    secret_key = 'KV1T805HV4'
    FY_ID = "XT00158"
    TOTP_KEY = "RQ6MDX7WXSULGZRQT6JOTNVE3EW6P6RK"
    PIN = "1234"

    URL_SEND_LOGIN_OTP = "https://api-t2.fyers.in/vagator/v2/send_login_otp_v2"
    res = requests.post(url=URL_SEND_LOGIN_OTP, json={"fy_id": getEncodedString(FY_ID), "app_id": "2"}).json()
    if datetime.now().second % 30 > 27: sleep(5)
    URL_VERIFY_OTP = "https://api-t2.fyers.in/vagator/v2/verify_otp"
    res2 = requests.post(url=URL_VERIFY_OTP,
                     json={"request_key": res["request_key"], "otp": pyotp.TOTP(TOTP_KEY).now()}).json()
    ses = requests.Session()
    URL_VERIFY_OTP2 = "https://api-t2.fyers.in/vagator/v2/verify_pin_v2"
    payload2 = {"request_key": res2["request_key"], "identity_type": "pin", "identifier": getEncodedString(PIN)}
    res3 = ses.post(url=URL_VERIFY_OTP2, json=payload2).json()
    ses.headers.update({
    'authorization': f"Bearer {res3['data']['access_token']}"
    })

    TOKENURL = "https://api-t1.fyers.in/api/v3/token"
    payload3 = {"fyers_id": FY_ID,
            "app_id": client_id[:-4],
            "redirect_uri": redirect_uri,
            "appType": "100", "code_challenge": "",
            "state": "None", "scope": "", "nonce": "", "response_type": "code", "create_cookie": True}

    res3 = ses.post(url=TOKENURL, json=payload3).json()
    url = res3['Url']
    parsed = urlparse(url)
    auth_code = parse_qs(parsed.query)['auth_code'][0]
    auth_code
    grant_type = "authorization_code"
    response_type = "code"
    session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key,
    redirect_uri=redirect_uri,
    response_type=response_type,
    grant_type=grant_type
    )

    session.set_token(auth_code)
    response = session.generate_token()
    access_token = response['access_token']
    BROKER_APP = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path=os.getcwd())



def get_ltp():
    global ltp
    return ltp


def BROKER_WEBSOCKET_INT():
    global  BROKER_SOCKET
    global client_id
    global access_token


    def onmessage(message):
        global ltp
        ltp[message['symbol']] = message['ltp']


    def onerror(message):
         print("Error:", message)


    def onclose(message):
        print("Connection closed:", message)


    def onopen():
        data_type = "SymbolUpdate"
        symbols = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX" , 'NSE:FINNIFTY-INDEX']
        BROKER_SOCKET.subscribe(symbols=symbols, data_type=data_type)
        BROKER_SOCKET.keep_running()


    token = f"{client_id}-100:{access_token}"


    BROKER_SOCKET = data_ws.FyersDataSocket(
        access_token=token,
        log_path="",
        litemode=True,
        write_to_file=False,
        reconnect=True,
        on_connect=onopen,
        on_close=onclose,
        on_error=onerror,
        on_message=onmessage
    )
    return BROKER_SOCKET


def subscribe_new_symbol(symbol):
    global BROKER_SOCKET
    BROKER_SOCKET.subscribe(symbols=[symbol], data_type="SymbolUpdate")

def unsubscribe_symbol(symbol):
    global BROKER_SOCKET
    BROKER_SOCKET.unsubscribe(symbols=[symbol], data_type="SymbolUpdate")







