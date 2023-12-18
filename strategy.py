import pandas as pd

from OrderMng import OrderMng
from OrderParam import OrderParam
import schedule
from datetime import datetime
from strategy_repo import STRATEGY_REPO


class StrategyFactory(STRATEGY_REPO):

    def __init__(self, name, mode,symbol,interval,expiry):
        super().__init__(name,symbol,interval)
        self.expiry = expiry
        self.index = 'NIFTY' if self.symbol == 'NSE:NIFTY50-INDEX' else (
            'BANKNIFTY' if symbol == 'NSE:NIFTYBANK-INDEX' else 'FINNIFTY')
        self.strike_interval = {'NSE:NIFTYBANK-INDEX': 100, 'NSE:NIFTY50-INDEX': 50, 'NSE:FINNIFTY-INDEX': 50}
        # initializing the variables
        self.signal = 0
        self.trade_flag = True
        self.ticker_space = pd.DataFrame()
        OrderMng.LIVE_FEED = self.LIVE_FEED
        self.OrderManger = OrderMng(mode, name)
        self.instrument_under_strategy = []
        self.scheduler = schedule.Scheduler()



    def get_instrument(self, option_type, step):
        # calculating option strike price
        interval = self.strike_interval[self.symbol]
        spot = self.LIVE_FEED.get_ltp(self.symbol)
        strike = lambda: (round(spot / interval)) * interval
        ATM = strike()
        stk = ATM + interval * step
        instrument = f'{self.index}{self.expiry}{option_type[0]}{stk}'
        # appending into the list for future use
        self.instrument_under_strategy.append(instrument)

        return instrument

    def Open_position(self):
        if not self.instrument_under_strategy:
            self.param = {}
            for key, value in OrderParam(self.strategy_name, self.signal).items():
                instrument = self.get_instrument(value['opt'], value['step'])
                self.param[instrument] = {'Instrument': instrument, 'Transtype': value['transtype'],
                                          'Qty': value['Qty']}

            # subscribing for instrument
            instrument_to_subscribe = [instrument for instrument in self.instrument_under_strategy if instrument not in self.LIVE_FEED.ltp]
            if instrument_to_subscribe:
                self.LIVE_FEED.subscribe_new_symbol(instrument_to_subscribe)

        # checking the  feed has been started for all instruments subscribe above then taking position
        if all([s in self.LIVE_FEED.ltp.keys() for s in self.instrument_under_strategy]):
            for instrument in self.instrument_under_strategy:
                success = self.OrderManger.Add_position(**self.param[instrument])
                if not success:
                    print(f'Unable to place order for {instrument} please check with broker terminal')
                    break
                else:
                    self.position = self.signal

            # once the order is placed , this function will be de-scheduled
            self.scheduler.clear()


    def on_tick(self):
        if self.position:
            self.STR_MTM = self.OrderManger.Live_MTM()
        # checking the scheduled task
        self.scheduler.run_pending()
        self.Exit_position_on_real_time()

    def monitor_signal(self):
        # updating ticker space
        if not self.position and self.trade_flag:
            self.signal = self.get_signal()
            if self.signal:
                 self.scheduler.every(4).seconds.do(self.Open_position)

        print(f'Monitor signal : {datetime.now(self.time_zone)} : {self.strategy_name}:{self.signal}')

        if self.position:
            self.trailing_stops_candle_close()

    def Exit_position_on_real_time(self):
        #   exit position on the live ltp basis on realtime
        if self.trade_flag:
            if self.position:
                if self.monitor_stop_live():
                    self.squaring_of_all_position_AT_ONCE()

            if datetime.now(self.time_zone).time() >= datetime.strptime('15:15:00', "%H:%M:%S").time():
                if self.position:
                    self.squaring_of_all_position_AT_ONCE()
                self.trade_flag = False

    def squaring_of_all_position_AT_ONCE(self):
        success = False
        # function ensure instrument will SELL trans_type will be executed first then hedge position

        sequence = {k: v for k, v in
                    sorted(self.OrderManger.Transtype.items(),
                           key=lambda item: (item[1] == 'BUY', item[1] == 'SELL'))}


        # ensuring every position is squared off if not break the loop else set open position to zero
        for instrument in sequence.keys():
            if not self.OrderManger.close_position(instrument, abs(self.OrderManger.net_qty[instrument])):
                success = False
                break
            else:
                success = True

        if success:
            self.position = 0
            self.refresh_var()

    def refresh_var(self):
        # updating mtm after order placement
        self.STR_MTM = self.OrderManger.CumMtm
        self.signal = 0
        self.stop = 0
        self.OrderManger.refresh_variable()
        # symbol to unsubscribe
        self.instrument_under_strategy = []







