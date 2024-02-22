import pandas as pd

from OrderMng import OrderMng
from OrderParam import OrderParam
import schedule
from datetime import datetime
from strategy_repo import STRATEGY_REPO


class StrategyFactory(STRATEGY_REPO):

    def __init__(self, name, mode,symbol,Components,interval,expiry):
        super().__init__(name,symbol,Components,interval)
        self.expiry = expiry
        self.index = 'NIFTY' if self.symbol == 'NSE:NIFTY50-INDEX' else (
            'BANKNIFTY' if symbol == 'NSE:NIFTYBANK-INDEX' else 'FINNIFTY')
        self.strike_interval = {'NSE:NIFTYBANK-INDEX': 100, 'NSE:NIFTY50-INDEX': 50, 'NSE:FINNIFTY-INDEX': 50}
        self.expiry_weekday = {'NSE:NIFTYBANK-INDEX':2, 'NSE:NIFTY50-INDEX': 3}
        # initializing the variables
        self.signal = 0
        self.spot = 0
        self.overnight_flag = False
        self.trade_flag = True
        self.ticker_space = pd.DataFrame()
        self.instrument_under_strategy = []
        self.scheduler = schedule.Scheduler()
        OrderMng.LIVE_FEED = self.LIVE_FEED
        self.OrderManger = OrderMng(mode, name,self)
        self.processed_flag = False

    def Is_Valid_time(self):
        valid_time = False
        if datetime.now(self.time_zone).time()>datetime.strptime('09:15:00', "%H:%M:%S").time():
            valid_time = True
        return valid_time

    def get_instrument(self, option_type, step):
        # calculating option strike price
        interval = self.strike_interval[self.symbol]
        self.spot = self.LIVE_FEED.get_ltp(self.symbol) if not self.spot else self.spot
        strike = lambda: (round(self.spot / interval)) * interval
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
                                          'Qty': value['Qty'],'signal':self.signal}

            # subscribing for instrument
            instrument_to_subscribe = [instrument for instrument in self.instrument_under_strategy if instrument not in self.LIVE_FEED.token.values()]
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
            self.spot = 0
            self.instrument_under_strategy = []
        else:
            print(f'Socket is not Opened yet,re-iterating the function')

    def on_tick(self):
        # updating the overnight position
        if self.Is_Valid_time():
            if not self.overnight_flag:
                self.Validate_OvernightPosition()
                if not self.scheduler.jobs:
                    self.scheduler.every(5).seconds.do(self.OrderManger.Update_OpenPosition)
            else:
                if not self.position and self.trade_flag and not self.processed_flag:
                    self.signal = self.get_signal()
                    if self.signal:
                        self.scheduler.every(5).seconds.do(self.Open_position)
                    self.processed_flag = True

        self.STR_MTM = round(self.OrderManger.Live_MTM(),2) if self.position else round(self.OrderManger.CumMtm,2)
        # checking the scheduled task
        self.scheduler.run_pending()
        self.Exit_position_on_real_time()

    def Exit_position_on_real_time(self):
        # if self.expiry_weekday[self.symbol] == datetime.now(self.time_zone).weekday():
        if datetime.now(self.time_zone).time() > datetime.strptime('15:15:00', "%H:%M:%S").time():
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
            self.position = self.position if self.OrderManger.net_qty else 0

    def Validate_OvernightPosition(self):
        if self.position:
            self.squaring_of_all_position_AT_ONCE()
            self.overnight_flag = True




