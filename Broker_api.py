from fyers_apiv3.FyersWebsocket import data_ws
class BROKER_API:
    TICKER_OBJ = False
    STRATEGY_RUN = False
    ltp = {}

    def __init__(self):
        self.BROKER_APP = None
        self.ACCESS_TOKEN = None
        self.socket_opened = False
        self.symbol_on_subscription = []

    def BROKER_WEBSOCKET_INT(self):

        def open_callback():  # Socket open callback function
            self.socket_opened = True
            data_type = 'SymbolUpdate'
            symbols = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX" , "NSE:FINNIFTY-INDEX"]
            self.BROKER_APP.subscribe(symbols =symbols ,data_type=data_type)
            self.BROKER_APP.keep_running()

        def socket_close():  # On Socket close this callback function will trigger
            self.socket_opened = False
            print("Closed")

        def socket_error(message):  # Socket Error Message will receive in this callback function
            print("Error :", message)

        def on_message(message):  # Socket feed data will receive in this callback function
            if 'ltp' in message:
                self.ltp[message['symbol']] = message['ltp']

        self.BROKER_APP = data_ws.FyersDataSocket(access_token=self.ACCESS_TOKEN , log_path='' , litemode=True,
                                                  write_to_file=False , reconnect=True , on_connect=open_callback,on_close=socket_close , on_error=socket_error,on_message=on_message)

        self.BROKER_APP.connect()

    def subscribe_new_symbol(self, symbols):
        symbols = [s for s in symbols if s not in self.symbol_on_subscription]

        if symbols:
            self.BROKER_APP.subscribe(symbols)
            for s in symbols:
                if s not in self.symbol_on_subscription:
                    self.symbol_on_subscription.append(s)

    def get_ltp(self, symbol):

        # try:
            return self.ltp[symbol]

        # except KeyError:
        #     return 0

    def stop_websocket(self):
        self.BROKER_APP.stop_websocket()


    def on_tick(self):

        if self.TICKER_OBJ:
            self.TICKER_OBJ.run_scheduler()
            #  monitoring strategy
        if self.STRATEGY_RUN:
            for key in self.STRATEGY_RUN.keys():
                self.STRATEGY_RUN[key].on_tick()






