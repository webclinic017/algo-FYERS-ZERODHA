import pandas as pd

from OrderMng import OrderMng
from OrderParam import OrderParam
import schedule
from datetime import datetime
import pandas_ta as ta
import pytz

class StrategyFactory:
    TICKER_OBJ = None
    LIVE_FEED = None
    STR_MTM = 0


    def __init__(self, name, mode, symbol, interval,expiry):
        self.strategy_name = name
        self.interval = interval
        self.symbol = symbol
        self.expiry = expiry
        self.index = 'NIFTY' if self.symbol == 'NSE:NIFTY50-INDEX' else (
            'BANKNIFTY' if symbol == 'NSE:BANKNIFTY_INDEX' else 'FINNIFTY')
        self.strike_interval = {'NSE:NIFTYBANK-INDEX': 100, 'NSE:NIFTY50-INDEX': 50, 'NSE:FINNIFTY-INDEX': 50}
        # initializing the variables
        self.time_zone = pytz.timezone('Asia/kolkata')
        self.position = 0
        self.signal = 0
        self.trade_flag = True
        self.ticker_space = pd.DataFrame()
        OrderMng.LIVE_FEED = self.LIVE_FEED
        self.OrderManger = OrderMng(mode, name)
        self.instrument_under_strategy = []
        self.scheduler = schedule.Scheduler()
        self.t1 = None
        self.indicator_val = {}


    def get_instrument(self, option_type, step):
        # calculating option strike price
        interval = self.strike_interval[self.symbol]
        spot = self.LIVE_FEED.get_ltp(self.symbol)
        strike = lambda: (round(spot / interval)) * interval
        ATM = strike()
        stk = ATM + interval * step
        instrument = f'NSE:{self.index}{self.expiry}{stk}{option_type}'
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
            self.LIVE_FEED.subscribe_new_symbol(self.instrument_under_strategy)

        # checking the  feed has been started for all instruments subscribe above then taking position

        if all([s in self.LIVE_FEED.ltp.keys() for s in self.instrument_under_strategy]):
            if all([self.OrderManger.Add_position(**self.param[instrument]) for instrument in self.instrument_under_strategy]):
                self.position = self.signal
            else:
                print('Unable to place order please check with broker terminal')

            # once the order is placed , this function will be de-scheduled
            self.scheduler.cancel_job(self.t1)

    def on_tick(self):
        if self.position:
           self.STR_MTM = self.OrderManger.Live_MTM()


        # checking the scheduled task
        self.scheduler.run_pending()
        # self.Exit_position_on_real_time()



    def cal_indicator_val(self):
        if self.strategy_name == '3EMA':
            #  calculating ema
            for n in [2, 5]:
                self.indicator_val[f'ema_{n}'] = ta.ema(self.ticker_space['close'], n)

    def long_signal(self):
        self.signal = 0
        if self.trade_flag:
            if self.strategy_name == '3EMA':
                if (self.indicator_val['ema_2'].iloc[-1] > self.indicator_val['ema_5'].iloc[-1]):
                    self.signal = 1

        return self.signal

    def short_signal(self):
        self.signal=0
        if self.trade_flag:
            if self.strategy_name=='3EMA':
                if (self.indicator_val['ema_2'].iloc[-1] < self.indicator_val['ema_5'].iloc[-1]):
                    self.signal = -1

        return self.signal

    def monitor_signal(self, ticker_space):
        # updating ticker space
        self.ticker_space = ticker_space[f'{self.symbol}_{self.interval}'].iloc[:-1]
        self.cal_indicator_val()
        if not self.position:
            if self.long_signal() or self.short_signal():
                self.t1 = self.scheduler.every(4).seconds.do(self.Open_position)

        if self.position:
            self.Exit_position_on_previous_candle()

    def Exit_position_on_previous_candle(self):
        # exit are based on previous candle basis rather than on ltp basis

        if self.position:
            if self.strategy_name == '3EMA':
                # write exit condition here
                if self.position > 0:
                    if self.short_signal():
                        self.squaring_of_all_position_AT_ONCE()

                elif self.position < 0:
                    if self.long_signal():
                        self.squaring_of_all_position_AT_ONCE()


    def Exit_position_on_real_time(self):
        #   exit position on the live ltp basis on realtime

        if self.position and self.trade_flag:
            if datetime.now(self.time_zone).time() > datetime.strptime('15:15:00', "%H:%M:%S").time():
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


    def average_position(self):
        # defining the condition for  average your position

        if self.position:
            pass

    def refresh_var(self):
        # updating mtm after order placement
        self.STR_MTM = self.OrderManger.CumMtm

        # removing instrument from ltp dictionary
        for s in self.instrument_under_strategy:
            self.LIVE_FEED.ltp.pop(s, None)
        # unsubscribing option instrument
        self.LIVE_FEED.unsubscribe_symbol(self.instrument_under_strategy)
        self.instrument_under_strategy = []
        self.signal = 0
        self.OrderManger.refresh_variable()

