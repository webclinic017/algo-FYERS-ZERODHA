import pandas as pd
from datetime import datetime,timedelta
import numpy as np
import pandas_ta as ta
import pickle as pk
from sklearn.decomposition import PCA

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
        self.pca_1 = None
        self.pca_2 = None
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
        self.bar_since = {name:bars for name,bars in zip(['SharpeRev', 'TREND_EMA','MOM_BURST'],[2, 1, 2])}

    def load_model(self):
        self.model_1 = self.get_model(1, 'ML')
        self.model_2 = self.get_model(2,'ML')
        self.pca_1 = self.get_model(1, 'PCA')
        self.pca_2 = self.get_model(2, 'PCA')

    def get_model(self,n,model):
        file_name = f'{self.strategy_name}_PCA_{n}' if model == 'PCA' else f'{self.strategy_name}_{n}'
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
            print(f'OnBarGetSignal:{datetime.now(self.time_zone)}:signal:{signal}:Index:{self.data.index[-1]}:{self.strategy_name}')


        return signal

    @property
    def get_params(self):
        param = None
        if self.strategy_name == 'SharpeRev':
            param = {'QLVL': 0.270999976567996,'dfactor': -9,'lags': 3,'lookback': 8,'normal_window': 147,'q_dn': 0.3276387458655868,'q_up': 0.8832153835407984,'window': 5}
        elif self.strategy_name == 'TREND_EMA':
            param = {'QLVL': 0.45970899103832763,'ang_1': 7,'ang_2': 19,'lags': 3,'lookback': 18,'lookback_1': 6,'lookback_2': 13,'lookback_3': 57,'normal_window': 83,'z': 10 , 'dfactor':0}
        elif self.strategy_name == 'MOM_BURST':
            param = {'QLVL': 0.5433837935924208,'dfactor': 12,'lags': 0,'lookback': 13,'normal_window': 188}
        return param

    @property
    def get_params_Stops(self):
        param = None
        if self.strategy_name == 'SharpeRev':
            param = {'atr_p': 8, 'factor': 0.8552449695830764}
        elif self.strategy_name == 'TREND_EMA':
            param = {'atr_p': 15, 'factor': 1.0059539772637485}
        elif self.strategy_name == 'MOM_BURST':
            param = {'atr_p': 19, 'factor': 1.5582004284936533}

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
            model_input = self.pca_1.transform(self.normalized_features.values[-1].reshape(1, -1))
            prediction = self.model_1.predict(model_input)
        else:
            model_input = self.pca_2.transform(self.normalized_features.values[-1].reshape(1, -1))
            prediction = self.model_2.predict(model_input)

        return 1 if prediction[0] else -1

    def MOM_BURST(self, lookback, normal_window, lags, QLVL, dfactor):
        # Initialization of variables

        features = pd.DataFrame()
        lookback = lookback - dfactor if (lookback - dfactor) >= 2 else lookback

        #       calculating indicator values
        v1, v2 = calculate_MOM_Burst(self.data, lookback)
        candle_range = self.data['high'] - self.data['low']
        rsi = ta.rsi(self.data['close'], lookback)

#       calculating strategy components(spr , quantiles)
        features['volatility'] = self.volatility
        features['mom_burst'] = v1
        features['pct_change'] = self.data['close'].pct_change()
        features['range_mean_vs_candle_range'] = candle_range / v2
        features['mom_burst_hh'] = v1 / v1.rolling(window=lookback).max().shift(1)
        features['mom_burst_ll'] = v1.rolling(window=lookback).min().shift(1) / v1
        features['rsi'] = rsi

        for col in ['range_mean_vs_candle_range', 'mom_burst_hh', 'mom_burst_ll']:
            features[f'{col}_STD'] = features[col].ewm(span=lookback).std()

#       lags values for the features
        if lags:
            lag_values = pd.DataFrame()
            for col in features.columns:
                for lag in range(1, lags + 1):
                    lag_values[f'{col}_{lag}'] = features[col].shift(lag)
            # concatenate the feature and lag features
            features = pd.concat([features, lag_values], axis=1)

        #       normalization the features
        normalized_features = self.Normalization(features, normal_window)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        return normalized_features

    def SharpeRev(self, lookback, q_dn, q_up, window, normal_window, lags, QLVL, dfactor):
        # Initialization of variables
        features = pd.DataFrame()
        lookback = lookback - dfactor if (lookback - dfactor) >= 2 else lookback

        #       calculating indicator values
        features['volatility'] = self.volatility
        mean = self.data['close'].pct_change().rolling(window=lookback).mean() * 100
        std = self.data['close'].pct_change().rolling(window=lookback).std() * 100
        pct_change = self.data['close'].pct_change() * 100
        spr = (pct_change - mean) / std
        EMA = self.data['close'].ewm(span=lookback).mean()
        #  calculating strategy components(spr , quantiles)
        features['spr'] = spr
        features['quan_up'] = features['spr'].rolling(window=window).quantile(q_up)
        features['quan_dn'] = features['spr'].rolling(window=window).quantile(q_dn)
        features['spr_quan_up'] = features['quan_up'] - features['spr']
        features['spr_quan_dn'] = features['spr'] - features['quan_dn']
        features['sentiment'] = EMA - self.data['close']

        if lags:
            lag_values = pd.DataFrame()
            for col in features.columns:
                for lag in range(1, lags + 1):
                    lag_values[f'{col}_{lag}'] = features[col].shift(lag)
                    # concatenate the feature and lag features
            features = pd.concat([features, lag_values], axis=1)

        #       normalization the features
        normalized_features = self.Normalization(features, normal_window)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek

        return normalized_features

    def TREND_EMA(self, lookback, lookback_1, lookback_2, lookback_3, ang_1, ang_2, z, normal_window,lags, QLVL ,dfactor):
        # Initialization of variables
        features = pd.DataFrame()

        #       calculating indicator values
        rsi = ta.rsi(self.data['close'], lookback)
        adx = ta.adx(self.data['high'], self.data['low'], self.data['close'], lookback)
        ema_1 = self.data['close'].ewm(span=lookback_1).mean()
        ema_2 = self.data['close'].ewm(span=lookback_2).mean()
        ema_3 = self.data['close'].ewm(span=lookback_3).mean()

        #       calculating degrees of emas
        angle_1_FAST = ta.slope(ema_1, ang_1)
        angle_2_FAST = ta.slope(ema_2, ang_1)
        angle_3_FAST = ta.slope(ema_3, ang_1)
        angle_1_SLOW = ta.slope(ema_1, ang_2)
        angle_2_SLOW = ta.slope(ema_2, ang_2)
        angle_3_SLOW = ta.slope(ema_3, ang_2)

        # calculating z score
        z_1 = Z_score(ema_1, z)
        z_2 = Z_score(ema_2, z)
        z_3 = Z_score(ema_3, z)
        z_4 = Z_score(rsi, z)

        # calculating strategy components
        features['volatility'] = self.volatility
        features['spr_1'] = ema_1 / ema_2
        features['spr_2'] = ema_2 / ema_3
        features['spr_3'] = ema_1 / ema_3
        features['ang_ratio_1_FAST'] = angle_1_FAST / angle_2_FAST
        features['ang_ratio_2_FAST'] = angle_2_FAST / angle_3_FAST
        features['ang_ratio_3_FAST'] = angle_1_FAST / angle_3_FAST
        features['ang_ratio_1_SLOW'] = angle_1_SLOW / angle_2_SLOW
        features['ang_ratio_2_SLOW'] = angle_2_SLOW / angle_3_SLOW
        features['ang_ratio_3_SLOW'] = angle_1_SLOW / angle_3_SLOW
        features['FAST_SLOW_1'] = angle_1_FAST / angle_1_SLOW
        features['FAST_SLOW_2'] = angle_2_FAST / angle_2_SLOW
        features['FAST_SLOW_1'] = angle_3_FAST / angle_3_SLOW
        features['Z_1'] = z_1
        features['Z_2'] = z_2
        features['Z_3'] = z_3
        features['Z_4'] = z_4
        features['rsi'] = rsi
        features['close_ema_1'] = self.data['close'] / ema_1
        features['close_ema_2'] = self.data['close'] / ema_2
        features['close_ema_3'] = self.data['close'] / ema_3

        features = pd.concat([features, adx], axis=1)

        lag_values = pd.DataFrame()
        for col in features.columns:
            for lag in range(1, lags):
                lag_values[f'{col}_{lag}'] = features[col].shift(lag)

        # concatenate the feature and lag features
        features = pd.concat([features, lag_values], axis=1)
        #       normalization the features
        normalized_features = self.Normalization(features, normal_window)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek

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
            self.entry_i = 0
            print(f'OnBarGetSignal:{datetime.now(self.time_zone)}:signal:{signal}:Index:{self.data.index[-1]}:{self.strategy_name}')


        return signal
