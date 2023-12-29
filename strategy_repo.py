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
        self.model = None
        self.model_1 = None
        self.model_2 = None
        self.quantile_DN = {}
        self.quantile_UP = {}
        self.load_model()
        self.time_series = []
        self.generate_timeseries()

    def load_model(self):
        if self.strategy_name == 'SharpeRev' or self.strategy_name == 'TREND_EMA':
            self.model_1 = self.get_model(n=1)
            self.model_2 = self.get_model(n=2)
        else:
            self.model = self.get_model()

    def get_model(self,n=0):
        file_name = f'{self.strategy_name}' if n == 0 else f'{self.strategy_name}_{n}'
        with open(f'{file_name}.pkl', 'rb') as file:
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
        param = None
        if self.strategy_name == 'TREND_EMA':
            param = {'QLVL': 0.22381997538692983,'ema': 11,'lookback_1': 7,'lookback_2': 16,'atr_p': 4,'factor': 1.1650394838756581,'lags_trend': 5,'dfactor': -8,'rsi_p': 3,'normal_window': 6}
        elif self.strategy_name == 'SharpeRev':
            param = {'window': 4,'lookback': 2,'q_up': 1.0,'q_dn': 0.1,'normal_window': 141,'atr_p': 8,'factor': 1.75,'lags_sharpe': 8,'dfactor': -20,'QLVL': 0.95}
        elif self.strategy_name == 'MOM_BURST':
            param = {'lookback': 2, 'normal_window': 182, 'atr_p': 8, 'factor': 1.665951088069996, 'lags_range': 1, 'dfactor': 5}

        return param

    @property
    def get_quantile(self):
        if self.model_1 and self.model_2:
            param = self.get_params
            log_return = np.log(self.dt['close'] / self.dt['close'].shift(1))
            vol = log_return.ewm(span=param['normal_window']).std()
            self.quantile_DN[self.strategy_name] = vol.rolling(window=param['normal_window']).quantile(param['QLVL'])
            self.quantile_UP[self.strategy_name] = vol.rolling(window=param['normal_window']).quantile(param['QLVL'])
            if vol.iloc[-1] < self.quantile_DN[self.strategy_name].iloc[-1]:
                self.model = self.model_1
            elif vol.iloc[-1] > self.quantile_UP[self.strategy_name].iloc[-1]:
                self.model = self.model_2
        else:
            self.quantile_UP = {'MOM_BURST': 0.0019052022355813324}
            self.quantile_DN = {'MOM_BURST':0.0009401364610806288}

        return self.quantile_UP[self.strategy_name],self.quantile_DN[self.strategy_name]

    def predictor(self,features):
        prediction = self.model.predict(features.values[-1].reshape(1,-1))
        signal = 1 if prediction[0] else -1
        return signal

    def is_valid_time_zone(self):
        cond1 = datetime.now(self.time_zone).time() > datetime.strptime('09:30:00', "%H:%M:%S").time()
        cond2 = datetime.now(self.time_zone).replace(microsecond=0,second=0) in self.time_series
        return cond1 and cond2

    def get_signal(self):
        features = None
        signal = 0
        if self.is_valid_time_zone():
            self.dt = self.TICKER.get_data(self.symbol, f'{self.interval}T')
            if self.strategy_name == 'TREND_EMA':
                features = self.TREND_EMA(**self.get_params)
            elif self.strategy_name == 'SharpeRev':
                features = self.Sharpe_Rev(**self.get_params)
            elif self.strategy_name == 'MOM_BURST':
                features = self.MOM_BURST(**self.get_params)

            signal = self.predictor(features)

        return signal

    def Normalization(self,features, normal_window):
        # dropping nan
        features = features.dropna(axis =0)

        # Calculate the mean values using a rolling window
        mean_val = features.rolling(window=normal_window).mean()

        # Calculate the standard deviation values using a rolling window
        std_val = features.rolling(window=normal_window).std()

        # Standardize the features using the calculated mean and standard deviation values
        standardized_features = (features - mean_val) / (std_val + 1e-8)

        # Drop NaN values that may result from the rolling window
        return standardized_features.dropna(axis=0)

    def Sharpe_Rev(self,lookback, q_dn,q_up, window,normal_window,lags_sharpe,dfactor,QLVL=None,factor=None, atr_p=None):
        lookback = int(lookback)
        window = int(window)
        normal_window = int(normal_window)
        lags = int(lags_sharpe)
        dfactor = int(dfactor)

        features = pd.DataFrame()

        # calculating indicators
        EMA, spr, = self.Dynamic_Indicator_SharpeRev(lookback,dfactor,normal_window)
        # calculating strategy components(spr , quantiles)
        features['spr'] = spr
        features['quan_up'] = features['spr'].rolling(window=window).quantile(q_up)
        features['quan_dn'] = features['spr'].rolling(window=window).quantile(q_dn)
        features['spr_quan_up'] = features['quan_up'] / features['spr']
        features['spr_quan_dn'] = features['spr'] / features['quan_dn']
        features['sentiment'] = EMA / self.dt['close']

        lag_values = pd.DataFrame()
        for col in features.columns:
            for lag in range(1, lags):
                lag_values[f'{col}_{lag}'] = features[col].shift(lag)

        # concatenate the feature and lag features
        features = pd.concat([features, lag_values], axis=1)
        # normalization the features
        normalized_features = self.Normalization(features, normal_window)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        return normalized_features

    def TREND_EMA(self,ema,lookback_1,lookback_2,rsi_p,normal_window,lags_trend,dfactor,QLVL=None,factor=None,atr_p=None):
        # conversion datatype
        ema = int(ema)
        lookback_1 = int(lookback_1)
        lookback_2 = int(lookback_2)
        normal_window = int(normal_window)
        lags = int(lags_trend)

        #   importing the dynamic indicators values
        v1,v2,v3,v4,v5 = self.Dynamic_Indicator_TREND_EMA(ema, lookback_1,lookback_2,dfactor,normal_window,rsi_p)
        features = pd.DataFrame()

        features['ema'] = v1
        features['rsi'] = v5
        features['angle_1'] = v2
        features['angle_2'] = v3
        features['vol'] = v4
        features['ema_close'] = features['ema'] / self.dt['close']
        features['angle_ratio'] = features['angle_1'] / features['angle_2']
        features['range_vol_1'] = (self.dt['high'] - self.dt['low'].shift(1)).rolling(window=lookback_1).std()
        features['range_vol_2'] = (self.dt['high'] - self.dt['low'].shift(1)).rolling(window=lookback_2).std()
        features['range_ratio'] = features['range_vol_1'] / features['range_vol_2']
        features['pct_change'] = self.dt['close'].pct_change()
        #         calculating GAPS
        GAP = pd.Series(np.nan, index=features.index)

        OPENING = features.loc[pd.Timestamp('09:15:00').time()]['pct_change']
        GAP.loc[OPENING.index] = np.where(OPENING > 0, 1, -1)
        GAP = GAP.fillna(method='ffill')

        lag_values = pd.DataFrame()
        for col in features.columns:
            for lag in range(1, lags):
                lag_values[f'{col}_{lag}'] = features[col].shift(lag)

        features = pd.concat([features, lag_values], axis=1)

        #   normalization the features
        normalized_features = self.Normalization(features, normal_window)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        normalized_features['GAP'] = GAP.loc[normalized_features.index]
        return normalized_features


    def MOM_BURST(self, lookback,normal_window,lags_range,dfactor,factor=None, atr_p=None):

        features = pd.DataFrame()

        # conversion of variables
        lookback = int(lookback)
        normal_window = int(normal_window)
        dfactor = int(dfactor)
        lags = int(lags_range)

        #   getting dynamic indicator values
        v1, v2 = self.Dynamic_Indicator_MOM_BURST(lookback, dfactor)
        candle_range = self.dt['high'] - self.dt['low']

        features['mom_burst'] = v1
        features['pct_change'] = self.dt['close'].pct_change()
        features['range_mean_vs_candle_range'] = candle_range / v2
        features['mom_burst_hh'] = v1 / v1.rolling(window=lookback).max().shift(1)
        features['mom_burst_ll'] = v1.rolling(window=lookback).min().shift(1) / v1

        for col in ['range_mean_vs_candle_range', 'mom_burst_hh', 'mom_burst_ll']:
            features[f'{col}_STD'] = features[col].ewm(span=lookback).std()

        #   calculating lagged values
        lag_values = pd.DataFrame()
        for col in features.columns:
            for lag in range(1, lags):
                lag_values[f'{col}_{lag}'] = features[col].shift(lag)

        features = pd.concat([features, lag_values], axis=1)

        #   normalization the features
        normalized_features = self.Normalization(features, normal_window)
        return normalized_features

    def Dynamic_Indicator_SharpeRev(self, window,dfactor,normal_window):
        UP ,DN = self.get_quantile

        log_return = np.log(self.dt['close'] / self.dt['close'].shift(1))
        vol = log_return.ewm(span=normal_window).std()

        # setting the window length dynamically
        WIN_UP = (window - dfactor) if (window - dfactor) >= 2 else window
        WIN_DN = (window + dfactor) if (window + dfactor) >= 2 else window

        #       calculating ema
        ema = self.dt['close'].ewm(span=window).mean()
        EMA_UP = self.dt['close'].ewm(span=WIN_UP).mean()
        EMA_DN = self.dt['close'].ewm(span=WIN_DN).mean()

        # calculating angle for lookback_2
        spr = self.dt['close'].pct_change(window) / self.dt['close'].rolling(window=window).std()
        SPR_UP = self.dt['close'].pct_change(WIN_UP) / self.dt['close'].rolling(window=WIN_UP).std()
        SPR_DN = self.dt['close'].pct_change(WIN_DN) / self.dt['close'].rolling(window=WIN_DN).std()

        #       setting dynamic indicator values
        ema[vol >= UP] = EMA_UP[vol >= UP]
        ema[vol <= DN] = EMA_DN[vol <= DN]

        spr[vol >= UP] = SPR_UP[vol >= UP]
        spr[vol <= DN] = SPR_DN[vol <= DN]

        return ema, spr

    def Dynamic_Indicator_TREND_EMA(self, window, lookback_1,lookback_2,dfactor,normal_window,rsi_p):
        UP, DN = self.get_quantile
        log_return = np.log(self.dt['close'] / self.dt['close'].shift(1))
        vol = log_return.ewm(span=normal_window).std()

        WIN_UP = (window - dfactor) if (window - dfactor) >= 2 else window
        WIN_DN = (window + dfactor) if (window + dfactor) >= 2 else window

        # setting the window length dynamically
        RSI_WIN_UP = (rsi_p - dfactor) if (rsi_p - dfactor) >= 2 else rsi_p
        RSI_WIN_DN = (rsi_p + dfactor) if (rsi_p + dfactor) >= 2 else rsi_p

        # calculating ema
        ema = self.dt['close'].ewm(span=window).mean()
        EMA_UP = self.dt['close'].ewm(span=WIN_UP).mean()
        EMA_DN = self.dt['close'].ewm(span=WIN_DN).mean()

        #  calculating rsi
        rsi = ta.rsi(self.dt['close'], rsi_p)
        RSI_UP = ta.rsi(self.dt['close'], RSI_WIN_UP)
        RSI_DN = ta.rsi(self.dt['close'], RSI_WIN_DN)

        # calculating angle for lookback_1
        angle_1 = line_angle(ema, lookback_1)
        ANG_UP_1 = line_angle(EMA_UP, lookback_1)
        ANG_DN_1 = line_angle(EMA_DN, lookback_1)

        # calculating angle for lookback_2
        angle_2 = line_angle(ema, lookback_2)
        ANG_UP_2 = line_angle(EMA_UP, lookback_2)
        ANG_DN_2 = line_angle(EMA_DN, lookback_2)

        # setting dynamic indicator values
        ema[vol >= UP] = EMA_UP[vol >= UP]
        ema[vol <= DN] = EMA_DN[vol <= DN]

        angle_1[vol >= UP] = ANG_UP_1[vol >= UP]
        angle_1[vol <= DN] = ANG_DN_1[vol <= DN]

        angle_2[vol >= UP] = ANG_UP_2[vol >= UP]
        angle_2[vol <= DN] = ANG_DN_2[vol <= DN]

        rsi[vol >= UP] = RSI_UP[vol >= UP]
        rsi[vol <= DN] = RSI_DN[vol <= DN]

        return ema, angle_1, angle_2,vol,rsi

    def Dynamic_Indicator_MOM_BURST(self,window, dfactor):
        UP, DN = self.get_quantile

        log_return = np.log(self.dt['close'] / self.dt['close'].shift(1))
        vol = log_return.ewm(span=10).std()

        # setting the window length dynamically
        WIN_UP = (window - dfactor) if (window - dfactor) >= 2 else window
        WIN_DN = (window + dfactor) if (window + dfactor) >= 2 else window

        #  calculating dynamic value of mom burst
        mom_burst, mean_range = calculate_MOM_Burst(self.dt, window)
        mom_burst_UP, mean_range_UP = calculate_MOM_Burst(self.dt, WIN_UP)
        mom_burst_DN, mean_range_DN = calculate_MOM_Burst(self.dt, WIN_DN)

        mom_burst[vol >= UP] = mom_burst_UP[vol >= UP]
        mom_burst[vol <= DN] = mom_burst_DN[vol <= DN]

        mean_range[vol >= UP] = mean_range_UP[vol >= UP]
        mean_range[vol <= DN] = mean_range_DN[vol <= DN]

        return mom_burst, mean_range

    def Dynamic_Stops(self):
        param = self.get_params
        window = param['atr_p']
        dfactor = param['dfactor']

        vol_period = param['normal_window'] if (self.strategy_name == 'SharpeRev') or (self.strategy_name == 'TREND_EMA') else 10

        UP,DN = self.get_quantile

        log_return = np.log(self.dt['close']/self.dt['close'].shift(1))
        vol = log_return.ewm(span = vol_period).std()

#       setting the window length dynamically
        WIN_UP = (window -dfactor) if (window -dfactor)>=2 else window
        WIN_DN = (window + dfactor) if (window + dfactor)>=2 else window

#       calculating ema
        atr = ta.atr(self.dt['high'], self.dt['low'],self.dt['close'], window)
        ATR_UP = ta.atr(self.dt['high'], self.dt['low'],self.dt['close'],WIN_UP)
        ATR_DN = ta.atr(self.dt['high'], self.dt['low'],self.dt['close'],WIN_DN)

#       setting dynamic values
        atr[vol>=UP] = ATR_UP[vol>=UP]

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
            if (self.position > 0) and (spot > 0) and self.stops:
                if self.stops > spot:
                    self.stops = 0
                    hit = True
            elif (self.position < 0) and (spot > 0) and self.stops:
                if self.stops < spot:
                    self.stops = 0
                    hit = True

        return hit

