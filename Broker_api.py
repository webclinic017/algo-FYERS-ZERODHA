from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws
from datetime import datetime
from  time import sleep
import os
import pyotp
import requests
from urllib.parse import parse_qs,urlparse
import base64


def getEncodedString(string):
    string = str(string)
    base64_bytes = base64.b64encode(string.encode("ascii"))
    return base64_bytes.decode("ascii")



class BROKER_API():
    TICKER_OBJ = None
    STRATEGY_RUN = None
    ltp = {}
    def __int__(self):
            self.BROKER_APP = None
            self.BROKER_SOCKET = None
            self.access_token = None
            self.client_id = None


    def login(self):

        redirect_uri = "https://127.0.0.1:5000/"
        self.client_id='IC8PF0KRVY-100'
        secret_key = 'KV1T805HV4'
        FY_ID = "XT00158"
        TOTP_KEY = "5MI36QR765HXYCG2JMW5OE5SGPEQUBLC"
        PIN = "2005"

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
                "app_id": self.client_id[:-4],
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
        client_id=self.client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type=response_type,
        grant_type=grant_type
        )

        session.set_token(auth_code)
        response = session.generate_token()
        self.access_token = response['access_token']
        self.BROKER_APP = fyersModel.FyersModel(client_id=self.client_id, is_async=False, token=self.access_token, log_path=os.getcwd())


    def BROKER_WEBSOCKET_INT(self):


        def onmessage(message):
                # print("Response:", message)
                self.ltp[message['symbol']] = message['ltp']


        #       updating ticker data space
                self.TICKER_OBJ.run_scheduler()
        #       monitoring strategy
                for key in self.STRATEGY_RUN.keys():
                    self.STRATEGY_RUN[key].on_tick()



        def onerror(message):
             print("Error:", message)


        def onclose(message):
            print("Connection closed:", message)


        def onopen():
            data_type = "SymbolUpdate"

            # Subscribe to the specified symbols and data type
            symbols = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX" , "NSE:FINNIFTY-INDEX"]
            self.BROKER_SOCKET.subscribe(symbols=symbols, data_type=data_type)
            self.BROKER_SOCKET.keep_running()


        token = f"{self.client_id}:{self.access_token}"


        self.BROKER_SOCKET = data_ws.FyersDataSocket(
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

        self.BROKER_SOCKET.connect()

    def subscribe_new_symbol(self,symbols):
        # symbol in list format
        self.BROKER_SOCKET.subscribe(symbols=symbols, data_type="SymbolUpdate")

    def unsubscribe_symbol(self,symbols):
        # symbol in list format
        self.BROKER_SOCKET.unsubscribe(symbols=symbols, data_type= "SymbolUpdate")

    def get_ltp(self,symbol):
        try:
            return self.ltp[symbol]

        except KeyError:
            return 0
