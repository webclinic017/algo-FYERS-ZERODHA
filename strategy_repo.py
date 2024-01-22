import pandas as pd
from datetime import datetime,timedelta
import numpy as np
import pandas_ta as ta
import pickle as pk

def Z_score(dt ,length):
    mean = dt.ewm(span=length).mean()
    std = dt.ewm(span=length).std()
    return (dt-mean)/std
def calculate_MOM_Burst( dt,lookback):
    candle_range = dt['high']-dt['low']
    mean_range = candle_range.rolling(window=lookback).mean()
    std_range = candle_range.rolling(window=lookback).std()
    mom_burst = (candle_range-mean_range)/std_range
    return mom_burst,mean_range

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
        self.model = None
        self.model_1 = None
        self.model_2 = None
        self.quantile_DN = {}
        self.quantile_UP = {}
        self.load_model()
        self.time_series = []
        self.generate_timeseries()
        self.executed_timeseries = set()
        self.normalized_features = None
        self.volatility = None
        self.data = None
        self.params = None
        self.entry_i = 0
        self.bar_since = {name:bars for name,bars in zip(['SharpeRev', 'TREND_EMA','MOM_BURST'],[3, 1, 1])}

    def load_model(self):
        self.model_1 = self.get_model(n=1)
        self.model_2 = self.get_model(n=2)

    def get_model(self,n=0):
        file_name = f'{self.strategy_name}' if n == 0 else f'{self.strategy_name}_{n}'
        with open(f'{file_name}.pkl', 'rb') as file:
            loaded_model = pk.load(file)
        return loaded_model

    def generate_timeseries(self):
        l1 = ['5T', '10T', '15T', '20T', '30T', '45T', '1h', '2h']
        l2 = [5, 10, 15, 20, 30, 45, 60, 120]
        minutes = {key: i for key, i in zip(l1, l2)}

        current_time = datetime.now(self.time_zone).replace(microsecond=0)
        start_time = current_time.replace(hour=9, minute=15, second=0)
        end_time = current_time.replace(hour=15, minute=30, second=0)

        self.time_series = [start_time]

        while start_time <= end_time:
            start_time += timedelta(minutes=minutes[self.interval])
            self.time_series.append(start_time)

    def is_valid_time_zone(self):
        cond1 = False
        cond2 = False
        current_time = datetime.now(self.time_zone).replace(microsecond=0,second=0)
        if current_time not in self.executed_timeseries:
            cond1 = datetime.now(self.time_zone).time() > datetime.strptime('09:30:00', "%H:%M:%S").time()
            cond2 = current_time in self.time_series
            self.executed_timeseries.add(current_time)
        return cond1 and cond2

    def get_signal(self):
        signal = 0
        if self.is_valid_time_zone():
            self.data = self.TICKER.get_data(self.symbol, f'{self.interval}')
            signal = self.get_predictions()

        return signal

    @property
    def get_params(self):
        param = None
        if self.strategy_name == 'SharpeRev':
            param = {'QLVL': 0.11544321161100671,'dfactor': -10,'lags_sharpe': 1,'lookback': 7,'normal_window': 136,'q_dn': 0.1461905704840355,'q_up': 0.8693154206226757,'window': 7}
        elif self.strategy_name == 'TREND_EMA':
            param = {'QLVL': 0.26913206445646576,'dfactor': 4,'ema': 20,'lags': 4,'lookback_1': 6,'lookback_2': 17,'normal_window': 50,'rsi_p': 20,'window': 126}
        elif self.strategy_name == 'MOM_BURST':
            param = {'QLVL': 0.38111824468001454,'dfactor': -2,'lags': 1,'lookback': 13,'normal_window': 154}
        return param

    @property
    def get_params_Stops(self):
        param = None
        if self.strategy_name == 'SharpeRev':
            param = {'atr_p': 11, 'factor': 1.4239362466314422}
        elif self.strategy_name == 'TREND_EMA':
            param = {'atr_p': 4, 'factor': 1.4958412728446742}
        elif self.strategy_name == 'MOM_BURST':
            param = {'atr_p': 19, 'factor': 1.3967186342264144}

        return param

    def Normalization(self,features,normal_window):
        features = features.dropna(axis=0)
        mean_val = features.rolling(window=normal_window).mean()
        std_val = features.rolling(window=normal_window).std()
        standardized_features = (features - mean_val) / (std_val + 1e-8)
        return standardized_features.dropna(axis=0)

    def calculate_volatility(self,normal_window,QLVL,vol_period=10):
        log_return = np.log(self.data['close'] / self.data['close'].shift(1))
        volatility = log_return.ewm(span=vol_period).std()
        VOL_Q = volatility.rolling(window=normal_window).quantile(QLVL)
        return volatility,VOL_Q.iloc[-1] < volatility.iloc[-1]

    def get_predictions(self):
        # getting strategy params
        self.params = self.get_params
        # calculating volatility and quantile lvl for splitting the dataset
        self.volatility, UP = self.calculate_volatility(self.params['normal_window'],self.params['QLVL'])
        # getting normalized features
        self.params['dfactor'] = self.params['dfactor'] if UP else 0
        if self.strategy_name == 'SharpeRev':
            self.normalized_features = self.SharpeRev(**self.params)
        elif self.strategy_name == 'TREND_EMA':
            self.normalized_features = self.TREND_EMA(**self.params)
        elif self.strategy_name == 'MOM_BURST':
            self.normalized_features = self.MOM_BURST(**self.params)

        return self.predictor(UP)

    def predictor(self,UP):
        prediction = None
        if UP:
            prediction = self.model_1.predict(self.normalized_features.values[-1].reshape(1,-1))
        else:
            prediction = self.model_2.predict(self.normalized_features.values[-1].reshape(1,-1))
        line_ = f'Time:{datetime.now(self.time_zone)}-Index:{self.normalized_features.index[-1]}:signal:{prediction[0]}'
        print(line_)
        print(self.normalized_features.iloc[-1])
        return 1 if prediction[0] else -1

    def SharpeRev(self,lookback, q_dn,q_up,window, normal_window,lags_sharpe, QLVL,dfactor):
        # initialization of variables
        features = pd.DataFrame()
        lookback = lookback - dfactor if (lookback - dfactor) >= 2 else lookback

        # calculating indicator values
        features['volatility'] = self.volatility
        mean = self.data['close'].pct_change().rolling(window=lookback).mean() * 100
        std = self.data['close'].pct_change().rolling(window=lookback).std() * 100
        pct_change = self.data['close'].pct_change() * 100
        spr = (pct_change - mean) / std
        EMA = self.data['close'].ewm(span=lookback).mean()

        # calculating strategy components (spr , quantiles)
        features['spr'] = spr
        features['quan_up'] = features['spr'].rolling(window=window).quantile(q_up)
        features['quan_dn'] = features['spr'].rolling(window=window).quantile(q_dn)
        features['spr_quan_up'] = features['quan_up'] - features['spr']
        features['spr_quan_dn'] = features['spr'] - features['quan_dn']
        features['sentiment'] = EMA - self.data['close']

        lag_values = pd.DataFrame()
        for col in features.columns:
            for lag in range(1, lags_sharpe):
                lag_values[f'{col}_{lag}'] = features[col].shift(lag)

        # merge the feature and lag features
        features = pd.concat([features, lag_values], axis=1)
        # normalization the features
        normalized_features = self.Normalization(features, normal_window)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        return normalized_features

    def TREND_EMA(self,ema,lookback_1 ,lookback_2 , rsi_p , normal_window , lags , QLVL , dfactor ,window):
        # initialization of variables
        features = pd.DataFrame()
        ema = ema - dfactor if (ema - dfactor) >= 2 else ema
        rsi_p = rsi_p - dfactor if (rsi_p - dfactor) >= 2 else rsi_p

        # calculating indicator values
        EMA = self.data['close'].ewm(span=ema).mean()
        rsi = ta.rsi(self.data['close'], rsi_p)
        angle_1 = ta.slope(EMA, lookback_1)
        angle_2 = ta.slope(EMA, lookback_2)

        # calculating strategy components
        features['volatility'] = self.volatility
        features['EMA'] = EMA
        features['rsi'] = rsi
        features['angle_1'] = angle_1
        features['angle_2'] = angle_2
        features['angle_diff'] = angle_1 / angle_2
        features['range_1_std'] = (self.data['high'] - self.data['low'].shift(1)).rolling(window=lookback_1).std()
        features['range_2_std'] = (self.data['high'] - self.data['low'].shift(1)).rolling(window=lookback_2).std()
        features['range_diff'] = features['range_1_std'] / features['range_2_std']
        features['ema_close'] = self.data['close'] / EMA
        features['pct_change'] = self.data['close'].pct_change()
        features['Zscore'] = Z_score(self.data['close'], window)

        lag_values = pd.DataFrame()
        for col in features.columns:
            for lag in range(1, lags):
                lag_values[f'{col}_{lag}'] = features[col].shift(lag)

        # merge the feature and lag features
        features = pd.concat([features, lag_values], axis=1)
        #       normalization the features
        normalized_features = self.Normalization(features, normal_window)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        return normalized_features
    def MOM_BURST(self,lookback,normal_window,lags ,QLVL , dfactor):
        # initialization of variables
        features = pd.DataFrame()
        lookback = lookback - dfactor if (lookback - dfactor) >= 2 else lookback

        # calculating indicator values
        v1, v2 = calculate_MOM_Burst(self.data, lookback)
        candle_range = self.data['high'] - self.data['low']

        # calculating strategy components
        features['volatility'] = self.volatility
        features['mom_burst'] = v1
        features['pct_change'] = self.data['close'].pct_change()
        features['range_mean_vs_candle_range'] = candle_range / v2
        features['mom_burst_hh'] = v1 / v1.rolling(window=lookback).max().shift(1)
        features['mom_burst_ll'] = v1.rolling(window=lookback).min().shift(1) / v1

        for col in ['range_mean_vs_candle_range', 'mom_burst_hh', 'mom_burst_ll']:
            features[f'{col}_STD'] = features[col].ewm(span=lookback).std()

        lag_values = pd.DataFrame()
        for col in features.columns:
            for lag in range(1, lags):
                lag_values[f'{col}_{lag}'] = features[col].shift(lag)

        # merger the feature and lag features
        features = pd.concat([features, lag_values], axis=1)
        # normalization the features
        normalized_features = self.Normalization(features, normal_window)
        # normalized_features['dayofweek'] = normalized_features.index.dayofweek
        return normalized_features

    def get_stops(self):
        params = self.get_params_Stops
        atr = ta.atr(self.data['high'],self.data['low'],self.data['close'],params['atr_p'])
        lower_bound = self.data['close'] - (params['factor'] * atr)
        upper_bound = self.data['close'] + (params['factor'] * atr)
        return lower_bound.iloc[-1] if self.position > 0 else upper_bound.iloc[-1]

    def trailing_stops_candle_close(self):
        if not self.stops:
            self.stops = self.get_stops()
        else:
            self.data = self.TICKER.get_data(self.symbol, f'{self.interval}')
            stp = self.get_stops()
            self.stops = max(stp,self.stops) if self.position > 0 else min(stp, self.stops)

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

    def verify_bar_since(self):
        signal = 0
        self.entry_i += 1
        if self.entry_i == self.bar_since[self.strategy_name]:
            self.data = self.TICKER.get_data(self.symbol, f'{self.interval}')
            signal = self.get_predictions()

        return signal
