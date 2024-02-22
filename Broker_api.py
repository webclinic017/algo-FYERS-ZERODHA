
from pya3 import*
import json

class BROKER_API:
    TICKER_OBJ = False
    STRATEGY_RUN = False
    ltp = {}

    def __init__(self):
        self.BROKER_APP = None
        self.socket_opened = None
        self.token = {'26009':"NSE:NIFTYBANK-INDEX", '26000':"NSE:NIFTY50-INDEX",'26037':'NSE:FINNIFTY-INDEX'}
        self.symbol_on_subscription = []

    def login(self):
        user = "286412"
        key = 'nUUtMteC10LJJ2pyrzI6KFKYq6GxqoLSFIWMUgUeozx5HiZqlKfOBa3GcancGhAKWy2VnKnYuHC6m1u5VqXLIsacja9io1rs8O19dG8PHlKCJCjWSCeZIWarmR0XiGlO'
        self.BROKER_APP = Aliceblue(user_id=user,api_key=key)
        self.BROKER_APP.get_session_id()
        self.get_contracts()

        return self.BROKER_APP

    def get_contracts(self):
        self.BROKER_APP.get_contract_master('NFO')

    @property
    def get_idx_info(self):
        sub = []
        typ = ['INDICES','INDICES','INDICES']
        for s,v in zip(typ,self.token.keys()):
            sub.append(self.BROKER_APP.get_instrument_by_token(s,int(v)))

        return sub

    def get_instrument_info(self,symbol):
        info = self.BROKER_APP.get_instrument_by_symbol('NFO', symbol)
        # recording token and its related symbol
        self.token[str(info[1])] = info[3]
        return info

    def subscribe_spot(self):
        self.BROKER_APP.subscribe(self.get_idx_info)

    def BROKER_WEBSOCKET_INT(self):

        def socket_open():  # Socket open callback function
            print('connected')
            self.socket_opened = True

        def socket_close():  # On Socket close this callback function will trigger
            self.socket_opened = False
            print("Closed")

        def socket_error(message):  # Socket Error Message will receive in this callback function
            print("Error :", message)

        def feed_data(message):  # Socket feed data will receive in this callback function
            feed_message = json.loads(message)
            if 'lp' in feed_message:
                self.ltp[self.token[str(feed_message['tk'])]] = float(feed_message['lp'])

        self.BROKER_APP.start_websocket(socket_open_callback=socket_open, socket_close_callback=socket_close,
                              socket_error_callback=socket_error, subscription_callback=feed_data,
                              run_in_background=True, market_depth=False)

        while not self.socket_opened:
            pass
        else:
            self.subscribe_spot()

    def subscribe_new_symbol(self, symbols):
        info = [self.get_instrument_info(s) for s in symbols if s not in self.symbol_on_subscription]
        if info:
            self.BROKER_APP.subscribe(info)
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

        if self.STRATEGY_RUN:
            for key in self.STRATEGY_RUN.keys():
                self.STRATEGY_RUN[key].on_tick()






