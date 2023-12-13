import pandas as pd
from datetime import datetime,timedelta
import numpy as np
import pandas_ta as ta
import pickle as pk


def line_angle(df_, n):
    angle = [np.nan] * len(df_)
    for i in range(n, len(df_)):
        angle[i] = np.arctan((df_[i] - df_[i-n]) / n) * 180 / np.pi
    return pd.Series(angle ,index = df_.index)
def calculate_MOM_Burst( dt ,lookback):

    candle_range = dt['high']-dt['low']
    mean_range = candle_range.rolling(window = lookback).mean()
    std_range = candle_range.rolling(window = lookback).std()
    mom_burst = (candle_range-mean_range)/std_range

    return mom_burst, mean_range

class STRATEGY_REPO:
    LIVE_FEED = None
    TICKER = None
    time_zone = None

    def __init__(self,name,symbol,interval):
        self.strategy_name = name
        self.symbol = symbol
        self.position = 0
        self.STR_MTM = 0
        self.stops = 0
        self.interval = interval
        self.upper_bound = None
        self.lower_bound = None
        self.dt = None
        self.model = self.load_model()
        self.time_series = []
        self.generate_timeseries()

    def load_model(self):
        with open(f'{self.strategy_name}.pkl', 'rb') as file:
            loaded_model = pk.load(file)
        return loaded_model

    def generate_timeseries(self):
        current_time = datetime.now(self.time_zone).replace(microsecond=0)
        start_time = current_time.replace(hour=9, minute=15, second=0)
        end_time = current_time.replace(hour=15, minute=30, second=0)

        self.time_series = [start_time]

        while start_time <= end_time:
            start_time += timedelta(minutes=self.interval)
            self.time_series.append(start_time)


    @property
    def get_params(self):
        param  = None
        if self.strategy_name == 'TREND_EMA':
            param = {'atr_p': 4.092838367992565, 'dfactor': -2.985501937441061, 'ema': 3.4811469724876796, 'factor': 1.4310393281932097,  'lags_trend': 7.2366422496508065,  'lookback_1': 4.7709018776363585, 'lookback_2': 9.988958079213829,  'normal_window': 198.1862263075428, 'rsi_p': 4.522014227783339}
        elif self.strategy_name == 'SharpRev':
            param = {'atr_p': 6.7925871327746705, 'dfactor': -15.295860712288212, 'factor': 1.2998100036407099, 'lags_sharpe': 8.196900677085193,  'lookback': 2.111490940149929,  'normal_window': 135.54978793309067, 'q_dn': 0.0466444187678002, 'q_up': 0.9990729998055132, 'rsi_p': 6.86580583920249, 'window': 9.504009982131006}

        elif self.strategy_name == 'ZSCORE':
            param = {'atr_p': 7.48244520895104, 'dfactor': 12.604043782251061, 'factor': 1.346960460205199, 'lags_range': 4.5207182858789725,  'lookback': 35.36604811044482, 'normal_window': 77.4371585817239, 'rsi_p': 3.9490513076367755}

        return param
        
    def predictor(self,features):
        prediction = self.model.predict(features.values)
        signal = pd.Series(np.where(prediction>0,1, -1),index=features.index)
        print('signal_before',signal.iloc[-1])
        signal = self.trading_halts(signal)
        return signal.iloc[-1]

    def is_valid_time_zone(self):
        return datetime.now(self.time_zone).replace(microsecond=0,second=0) in self.time_series

    def get_signal(self):
        features = None
        signal = 0
        if self.is_valid_time_zone():
            self.dt = self.TICKER.get_data(self.symbol, f'{self.interval}T')
            if self.strategy_name == 'TREND_EMA':
                features = self.TREND_EMA(**self.get_params)
            elif self.strategy_name == 'SharpeRev':
                features = self.Sharpe_Rev(**self.get_params)
            elif self.strategy_name == 'ZSCORE':
                features = self.ZSCORE(**self.get_params)

            signal = self.predictor(features)
            print(self.strategy_name ,signal)
        return signal

    def Normalization(self,features, normal_window):
        # Calculate the mean values using a rolling window
        mean_val = features.rolling(window=normal_window).mean()

        # Calculate the standard deviation values using a rolling window
        std_val = features.rolling(window=normal_window).std()

        # Standardize the features using the calculated mean and standard deviation values
        standardized_features = (features - mean_val) / (std_val + 1e-8)

        # Drop NaN values that may result from the rolling window
        return standardized_features.dropna(axis=0)


    def Sharpe_Rev(self,lookback, q_dn ,q_up, rsi_p, window, normal_window ,lags_sharpe , dfactor , factor =None, atr_p = None):
        lookback = int(lookback)
        window = int(window)
        normal_window = int(normal_window)
        lags = int(lags_sharpe)
        dfactor = int(dfactor)

        features = pd.DataFrame()
        #   calculating indicators

        EMA, rsi, spr, = self.Dynamic_Indicator_SharpeRev(lookback, rsi_p, dfactor)

        #   calculating strategy components(spr , quantiles)
        features['spr'] = spr
        features['quan_up'] = features['spr'].rolling(window=window).quantile(q_up)
        features['quan_dn'] = features['spr'].rolling(window=window).quantile(q_dn)
        features['spr_quan_up'] = features['quan_up'] / features['spr']
        features['spr_quan_dn'] = features['spr'] / features['quan_dn']
        features['rsi_UP'] = rsi / 55
        features['rsi_DN'] = 45 / rsi
        features['sentiment'] = EMA / self.dt['close']

        lag_values = pd.DataFrame()
        for col in features.columns:
            for lag in range(1, lags):
                lag_values[f'{col}_{lag}'] = features[col].shift(lag)

        # concatenate the feature and lag features
        features = pd.concat([features, lag_values], axis=1)

        #   normalization the features
        normalized_features = self.Normalization(features, normal_window)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        return normalized_features

    def TREND_EMA(self,ema,lookback_1,lookback_2,rsi_p,normal_window ,lags_trend,dfactor , factor=None, atr_p = None):
        # conversion datatype
        ema = int(ema)
        lookback_1 = int(lookback_1)
        lookback_2 = int(lookback_2)
        normal_window = int(normal_window)
        lags = int(lags_trend)

        #   importing the dynamic indicators values
        v1, v2, v3, v4 = self.Dynamic_Indicator_TREND_EMA(ema, lookback_1, lookback_2, dfactor)
        features = pd.DataFrame()

        rsi = ta.rsi(self.dt['close'], rsi_p)

        #   creating dataset for features
        features['ema'] = v1
        features['rsi'] = rsi
        features['angle_1'] = v2
        features['angle_2'] = v3
        features['vol'] = v4
        features['rsi_UP'] = rsi / 55
        features['rsi_DN'] = 45 / rsi
        features['ema_close'] = features['ema'] / self.dt['close']
        features['angle_ratio'] = features['angle_1'] / features['angle_2']
        features['range_vol_1'] = (self.dt['high'] - self.dt['low'].shift(1)).rolling(window=lookback_1).std()
        features['range_vol_2'] = (self.dt['high'] - self.dt['low'].shift(1)).rolling(window=lookback_2).std()
        features['range_ratio'] = features['range_vol_1'] / features['range_vol_2']

        lag_values = pd.DataFrame()
        for col in features.columns:
            for lag in range(1, lags):
                lag_values[f'{col}_{lag}'] = features[col].shift(lag)

        features = pd.concat([features, lag_values], axis=1)

        #   normalization the features
        normalized_features = self.Normalization(features, normal_window)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        return normalized_features

    def ZSCORE(self,lookback , rsi_p , normal_window, lags_range, dfactor, factor = None, atr_p = None):
        features = pd.DataFrame()
        #   conversion of variables
        lookback = int(lookback)
        rsi_p = int(rsi_p)
        normal_window = int(normal_window)
        dfactor = int(dfactor)
        lags = int(lags_range)

        #   getting dynamic indicator values
        v1, v2, v3, v4 = self.Dynamic_Indicator_ZSCORE( lookback, rsi_p, dfactor)
        candle_range = self.dt['high'] - self.dt['low']

        features['mom_burst'] = v1
        features['vol'] = v3
        features['rsi_UP'] = v2 / 55
        features['rsi_DN'] = 45 / v2
        features['pct_change'] = self.dt['close'].pct_change()
        features['range_mean_vs_candle_range'] = candle_range / v4

        #   calculating lagged values
        lag_values = pd.DataFrame()
        for col in features.columns:
            for lag in range(1, lags):
                lag_values[f'{col}_{lag}'] = features[col].shift(lag)

        features = pd.concat([features, lag_values], axis=1)

        #   normalization the features
        normalized_features = self.Normalization(features, normal_window)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        return normalized_features

    def Dynamic_Indicator_SharpeRev(self, window, rsi_p, dfactor):
        UP = 0.0025106634457647357
        DN = 0.001488458217788889

        log_return = np.log(self.dt['close'] / self.dt['close'].shift(1))
        vol = log_return.ewm(span=10).std()

        # setting the window length dynamically
        WIN_UP = (window - dfactor) if (window - dfactor) >= 2 else window
        WIN_DN = (window + dfactor) if (window + dfactor) >= 2 else window

        #       calculating ema
        ema = self.dt['close'].ewm(span=window).mean()
        EMA_UP = self.dt['close'].ewm(span=WIN_UP).mean()
        EMA_DN = self.dt['close'].ewm(span=WIN_DN).mean()

        #       calculating angle for lookback_1
        WIN_UP_RSI = (rsi_p - dfactor) if (rsi_p - dfactor) >= 2 else rsi_p
        WIN_DN_RSI = (rsi_p + dfactor) if (rsi_p + dfactor) >= 2 else rsi_p

        rsi = ta.rsi(self.dt['close'], rsi_p)
        RSI_UP = ta.rsi(self.dt['close'], WIN_UP_RSI)
        RSI_DN = ta.rsi(self.dt['close'], WIN_DN_RSI)

        #       calculating angle for lookback_2
        spr = self.dt['close'].pct_change(window) / self.dt['close'].rolling(window=window).std()
        SPR_UP = self.dt['close'].pct_change(WIN_UP) / self.dt['close'].rolling(window=WIN_UP).std()
        SPR_DN = self.dt['close'].pct_change(WIN_DN) / self.dt['close'].rolling(window=WIN_DN).std()

        #       setting dynamic indicator values
        ema[vol >= UP] = EMA_UP[vol >= UP]
        ema[vol <= DN] = EMA_DN[vol <= DN]

        rsi[vol >= UP] = RSI_UP[vol >= UP]
        rsi[vol <= DN] = RSI_DN[vol <= DN]

        spr[vol >= UP] = SPR_UP[vol >= UP]
        spr[vol <= DN] = SPR_DN[vol <= DN]

        return ema, rsi, spr

    def Dynamic_Indicator_TREND_EMA(self, window, lookback_1, lookback_2, dfactor):
        UP = 0.0025106634457647357
        DN = 0.001488458217788889

        log_return = np.log(self.dt['close'] / self.dt['close'].shift(1))
        vol = log_return.ewm(span=10).std()

        WIN_UP = (window - dfactor) if (window - dfactor) >= 2 else window
        WIN_DN = (window + dfactor) if (window + dfactor) >= 2 else window

        #       calculating ema
        ema = self.dt['close'].ewm(span=window).mean()
        EMA_UP = self.dt['close'].ewm(span=WIN_UP).mean()
        EMA_DN = self.dt['close'].ewm(span=WIN_DN).mean()

        #       calculating angle for lookback_1
        angle_1 = line_angle(ema, lookback_1)
        ANG_UP_1 = line_angle(EMA_UP, lookback_1)
        ANG_DN_1 = line_angle(EMA_DN, lookback_1)

        #       calculating angle for lookback_2
        angle_2 = line_angle(ema, lookback_2)
        ANG_UP_2 = line_angle(EMA_UP, lookback_2)
        ANG_DN_2 = line_angle(EMA_DN, lookback_2)

        #         setting dynamic indicator values
        ema[vol >= UP] = EMA_UP[vol >= UP]
        ema[vol <= DN] = EMA_DN[vol <= DN]

        angle_1[vol >= UP] = ANG_UP_1[vol >= UP]
        angle_1[vol <= DN] = ANG_DN_1[vol <= DN]

        angle_2[vol >= UP] = ANG_UP_2[vol >= UP]
        angle_2[vol <= DN] = ANG_DN_2[vol <= DN]

        return ema, angle_1, angle_2, vol

    def Dynamic_Indicator_ZSCORE( self, window, rsi_p, dfactor):
        UP = 0.0025106634457647357
        DN = 0.001488458217788889

        log_return = np.log(self.dt['close'] / self.dt['close'].shift(1))
        vol = log_return.ewm(span=10).std()

        # setting the window length dynamically
        WIN_UP = (window - dfactor) if (window - dfactor) >= 2 else window
        WIN_DN = (window + dfactor) if (window + dfactor) >= 2 else window

        #       calculating dynamic value of mom burst
        mom_burst, mean_range = calculate_MOM_Burst(self.dt, window)
        mom_burst_UP, mean_range_UP = calculate_MOM_Burst(self.dt, WIN_UP)
        mom_burst_DN, mean_range_DN = calculate_MOM_Burst(self.dt, WIN_DN)

        #       calculating dynamic window
        WIN_UP_RSI = (rsi_p - dfactor) if (rsi_p - dfactor) >= 2 else rsi_p
        WIN_DN_RSI = (rsi_p + dfactor) if (rsi_p + dfactor) >= 2 else rsi_p

        #       calculating rsi indicator values
        rsi = ta.rsi(self.dt['close'], rsi_p)
        RSI_UP = ta.rsi(self.dt['close'], WIN_UP_RSI)
        RSI_DN = ta.rsi(self.dt['close'], WIN_DN_RSI)

        #       setting dynamic indicator values
        rsi[vol >= UP] = RSI_UP[vol >= UP]
        rsi[vol <= DN] = RSI_DN[vol <= DN]

        mom_burst[vol >= UP] = mom_burst_UP[vol >= UP]
        mom_burst[vol <= DN] = mom_burst_DN[vol <= DN]

        mean_range[vol >= UP] = mean_range_UP[vol >= UP]
        mean_range[vol <= DN] = mean_range_DN[vol <= DN]

        return mom_burst, rsi, vol, mean_range

    def Dynamic_Stops(self):
        param = self.get_params
        window = param['atr_p']
        dfactor = param['dfactor']

        UP = 0.0025106634457647357
        DN = 0.001488458217788889

        log_return = np.log(self.dt['close']/self.dt['close'].shift(1))
        vol = log_return.ewm(span = 10).std()

#       setting the window length dynamically
        WIN_UP = (window -dfactor) if (window -dfactor)>=2 else window
        WIN_DN = (window + dfactor) if (window + dfactor)>=2 else window

#       calculating ema
        atr = ta.atr(self.dt['high'], self.dt['low'],self.dt['close'], window)
        ATR_UP = ta.atr(self.dt['high'], self.dt['low'],self.dt['close'],WIN_UP)
        ATR_DN = ta.atr(self.dt['high'], self.dt['low'],self.dt['close'],WIN_DN)

#       setting dynamic values
        atr[vol>=UP] = ATR_UP[vol>=UP]
        atr[vol<=DN] = ATR_DN[vol<=DN]

        upper_bound = self.dt['close'] + (param['factor'] * atr)
        lower_bound = self.dt['close'] - (param['factor'] * atr)
        return upper_bound,lower_bound

    def Set_Stops(self):
            if self.position and not self.stops:
                self.upper_bound,self.lower_bound = self.Dynamic_Stops()
                self.stops = self.lower_bound.iloc[-1] if self.position > 0 else self.upper_bound.iloc[-1]

    def trailing_stops_candle_close(self):
        self.Set_Stops()
        if self.is_valid_time_zone():
            self.dt = self.TICKER.get_data(self.symbol, f'{self.interval}T')
            self.upper_bound,self.lower_bound = self.Dynamic_Stops()
            self.stops = max(self.lower_bound.iloc[-1],self.stops) if self.position > 0 else min(self.upper_bound.iloc[-1],self.stops)

    def monitor_stop_live(self):
        hit = False
        spot = 0
        if self.position:
            spot = self.LIVE_FEED.get_ltp(self.symbol)
            if (self.position > 0) and (spot > 0):
                if self.stops > spot:
                    self.stops = 0
                    hit = True
            elif (self.position < 0) and (spot > 0):
                if self.stops < spot:
                    self.stops = 0
                    hit = True

        return hit

    def trading_halts(self,  signal):
        if self.strategy_name == 'SharpeRev':
            TRADE_HAULT = [("14:31:00", "15:16:00")]
            for halt in TRADE_HAULT:
                signal.loc[signal.between_time(halt[0], halt[1]).index] = 0

        elif self.strategy_name == 'ZSCORE':
            TRADE_HAULT = [("09:30:00", "10:59:00"), ("13:31:00", "14:30:00")]
            for halt in TRADE_HAULT:
                signal.loc[signal.between_time(halt[0], halt[1]).index] = 0

        return signal

