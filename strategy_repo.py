
import pandas_ta as ta
import numpy as np
import pandas as pd
from datetime import datetime,timedelta


def line_angle(df_, n):
    angle = [np.nan] * len(df_)
    for i in range(n, len(df_)):
        angle[i] = np.arctan((df_[i] - df_[i-n]) / n) * 180 / np.pi
    return pd.Series(angle,index=df_.index)


class STRATEGY_REPO:
    LIVE_FEED = None
    TICKER = None
    time_zone = None

    def __init__(self, name, symbol, interval):
        self.strategy_name = name
        self.symbol = symbol
        self.interval = interval
        self.position = 0
        self.STR_MTM = 0
        self.df = None
        self.stop = None
        self.time_series = []
        self.generate_timeseries()

    def generate_timeseries(self):
        current_time = datetime.now(self.time_zone).replace(microsecond=0)
        start_time = current_time.replace(hour=9, minute=15, second=0)
        end_time = current_time.replace(hour=15, minute=30, second=0)

        self.time_series = [start_time]

        while start_time <= end_time:
            start_time += timedelta(minutes=self.interval)
            self.time_series.append(start_time)

    def long_signal(self):
        signal = False
        if datetime.now(self.time_zone).replace(microsecond=0,second=0) in self.time_series:
            self.df = self.TICKER.get_data(self.symbol, f'{self.interval}T')

            if self.strategy_name == '3EMA':
                spr = 0.015
                rsi_val_up = 64.79724715724147

                ema_1 = ta.ema(self.df['close'], 5)
                ema_2 = ta.ema(self.df['close'], 22)
                ema_3 = ta.ema(self.df['close'], 47)
                rsi = ta.rsi(self.df['close'], 6)
                spr_ratio = ema_2.iloc[-1] / ema_3.iloc[-1]

                cond1 = (ema_1.iloc[-1] > ema_2.iloc[-1]) & (ema_2.iloc[-1] > ema_3.iloc[-1])
                cond2 = (rsi.iloc[-1] >= rsi_val_up) & (spr_ratio > (1 + spr / 100))
                cond3 = ((ema_1.iloc[-1] > self.df['close'].iloc[-2]) & (ema_1.iloc[-1] < self.df['close'].iloc[-1]) &
                         (self.df['open'].iloc[-1] < self.df['close'].iloc[-1]))

                # signal = cond1 & cond2 & cond3
                signal = 1

                if signal:
                    factor = 0.5
                    # factor = 2.5
                    lower_bound = self.df['close'] - (factor * ta.atr(self.df['high'], self.df['low'], self.df['close'], 9))
                    self.stop = lower_bound.iloc[-1]


            elif self.strategy_name == '15_119_MA':
                rsi_val = 58.13729793460143
                ma_ang = 55

                ma_1 = self.df['close'].rolling(window=15).mean()
                ma_2 = self.df['close'].rolling(window=119).mean()
                ang = line_angle(ma_1, 7)
                rsi = ta.rsi(self.df['close'], 5)

                cond1 = (self.df['close'].iloc[-1] > ma_1.iloc[-1]) & (ma_1.iloc[-1] > ma_2.iloc[-1])
                cond2 = (ang.iloc[-1] > ma_ang) & (rsi_val < rsi.iloc[-1])

                # signal = cond1 & cond2
                signal = 1

                if signal:
                    factor = 0.5
                    # factor = 2.5
                    lower_bound = self.df['close'] - (factor * ta.atr(self.df['high'], self.df['low'], self.df['close'], 5))
                    self.stop = lower_bound.iloc[-1]


            elif self.strategy_name == 'MA_long_cross':
                rsi_val = 50.558788896861614

                long_ema = ta.ema(self.df['close'], 22)
                short_ema = ta.ema(self.df['close'], 5)
                rsi = ta.rsi(self.df['close'], 12)

                cond1 = (long_ema.iloc[-1] < short_ema.iloc[-1]) & (long_ema.iloc[-2] > short_ema.iloc[-2])
                cond2 = (rsi.iloc[-1] > rsi_val)

                signal = cond1 & cond2

                if signal:
                    factor = 0.5
                    lower_bound = self.df['close'] - factor * ta.atr(self.df['high'], self.df['low'], self.df['close'], 8)
                    self.stop = lower_bound.iloc[-1]

            elif self.strategy_name == 'Mean_Rev_BNF':
                q_dn = 0.039806606760467704
                sma = self.df['close'].rolling(window=4).mean()
                spr = self.df['close']/sma
                quan_down = spr.quantile(q_dn)

                # signal = (quan_down > spr.iloc[-2]) & (quan_down < spr.iloc[-1])
                signal = 1

                if signal:
                    factor = 0.5
                    # factor = 1.4036476588918747
                    lower_bound = self.df['close'] - factor * ta.atr(self.df['high'], self.df['low'],self.df['close'], 5)
                    self.stop = lower_bound.iloc[-1]

        return signal

    def short_signal(self):
        signal = False
        if datetime.now(self.time_zone).replace(microsecond=0, second=0) in self.time_series:
            self.df = self.TICKER.get_data(self.symbol, f'{self.interval}T')

            if self.strategy_name == 'Mean_Rev_BNF':
                q_up = 0.9501989777311063
                sma = self.df['close'].rolling(window=4).mean()
                spr = self.df['close'] / sma
                quan_up = spr.quantile(q_up)

                signal = (quan_up < spr.iloc[-2]) & (quan_up > spr.iloc[-1])

                if signal:
                    factor = 1.4036476588918747
                    upper_bound = self.df['close'] + factor * ta.atr(self.df['high'], self.df['low'], self.df['close'], 5)
                    self.stop = upper_bound.iloc[- 1]


        return signal

    def trailing_stops_candle_close(self):
        self.df = self.TICKER.get_data(self.symbol, f'{self.interval}T')

        if self.position > 0:
            if self.strategy_name == '3EMA':
                factor = 0.75
                # factor = 2.5
                lower_bound = self.df['close'] - factor * ta.atr(self.df['high'], self.df['low'], self.df['close'], 9)
                self.stop = max(self.stop, lower_bound.iloc[-1])


            elif self.strategy_name == '15_119_MA':
                factor = 0.75
                # factor = 2.5
                lower_bound = self.df['close'] - factor * ta.atr(self.df['high'], self.df['low'], self.df['close'], 5)
                self.stop = max(self.stop, lower_bound.iloc[-1])

            elif self.strategy_name == 'MA_long_cross':
                factor = 0.5
                lower_bound = self.df['close'] - factor * ta.atr(self.df['high'], self.df['low'], self.df['close'], 8)
                self.stop = max(self.stop, lower_bound.iloc[-1])

            elif self.strategy_name == 'Mean_Rev_BNF':
                factor = 0.75
                # factor = 1.4036476588918747
                lower_bound = self.df['close'] - factor * ta.atr(self.df['high'], self.df['low'], self.df['close'], 5)
                self.stop = max(self.stop, lower_bound.iloc[-1])

        elif self.position < 0:
            if self.strategy_name == 'Mean_Rev_BNF':
                factor = 0.75
                # factor = 1.4036476588918747
                upper_bound = self.df['close'] + factor * ta.atr(self.df['high'], self.df['low'], self.df['close'], 5)
                self.stop = min(upper_bound.iloc[- 1],self.stop)


    def monitor_stops_candle_close(self):
        hit = False
        if self.strategy_name == 'MA_long_cross':
            rsi_val_dn = 23.777431183856805
            rsi = ta.rsi(self.df['close'], 12)
            if rsi.iloc[-1] < rsi_val_dn:
                hit = True

        return hit

    def monitor_stop_live(self):
        hit = False
        spot = 0
        if self.position:
            if self.strategy_name in ['3EMA', '15_119_MA', 'MA_long_cross','Mean_Rev_BNF']:
                spot = self.LIVE_FEED.get_ltp(self.symbol)
                if (self.position > 0) and (spot > 0):
                    if self.stop > spot:
                        hit = True
                elif (self.position < 0) and (spot > 0):
                    if self.stop < spot:
                        hit = True

        return hit



