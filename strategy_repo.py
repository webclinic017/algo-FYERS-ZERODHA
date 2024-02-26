import pandas as pd
from datetime import datetime,timedelta
import numpy as np
import pandas_ta as ta
import pickle as pk
from sklearn.decomposition import PCA
from hmmlearn import hmm

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

def line_angle(df_, n):
    angle = np.full_like(df_, np.nan)  # Initialize with NaNs

    for i in range(n, len(df_)):
        dist = i - (i - n)
        if dist != 0:
            angle[i] = np.arctan((df_.iloc[i] - df_.iloc[i - n]) / dist) * 180 / np.pi

    return pd.Series(angle, index=df_.index)

class STRATEGY_REPO:
    LIVE_FEED = None
    TICKER = None
    time_zone = None

    def __init__(self,name,symbol,Components, interval):
        self.strategy_name = name
        self.symbol = symbol
        self.Components = Components
        self.position = 0
        self.normalized_features = None
        self.data = None
        self.params = None
        self.STR_MTM = 0
        self.interval = interval
        self.model_1 = None
        self.pca_1 = None
        self.regime_model_1 = None
        self.load_model()

    def load_model(self):
        self.model_1 = self.get_model(1, 'ML')
        self.pca_1 = self.get_model(1, 'PCA')
        self.regime_model_1 = self.get_model(1, 'REGIME')

    def get_model(self, n, model):
        file_name = f'{self.strategy_name}_PCA_{n}' if model == 'PCA' else (f'{self.strategy_name}_REGIME_{n}' if model == 'REGIME' else f'{self.strategy_name}_{n}')
        with open(f'{file_name}.pkl', 'rb') as file:
            loaded_model = pk.load(file)
        return loaded_model

    def get_signal(self):
        self.data = self.TICKER.get_data(self.symbol, f'{self.interval}')
        self.generate_features()
        return self.get_prediction()

    def get_prediction(self):
        model_input = self.pca_1.transform(self.normalized_features.values[-1].reshape(1, -1))
        prediction = self.model_1.predict(model_input)
        return prediction[-1]

    @property
    def get_params(self):
        param = None
        if self.strategy_name == 'TREND_EMA':
           param = {'lags': 0,'lookback_1': 8,'lookback_2': 10,'normal_window': 35,'window': 5}
        elif self.strategy_name == 'SharpeRev':
            param = {'lags': 5,'lookback': 25,'normal_window': 10,'q_dn': 0.35,'q_up': 0.85,'window': 5}
        elif self.strategy_name == 'MOM_BURST':
            param = {'lags': 5,'lookback': 30,'normal_window': 135}

        return param

    def Normalization(self, features, normal_window=10, normalization=True):
        if normalization:
            features = features.dropna(axis=0)
            mean_val = features.rolling(window=normal_window).mean()
            std_val = features.rolling(window=normal_window).std()
            standardized_features = (features - mean_val) / (std_val + 1e-8)
        else:
            standardized_features = features

        return standardized_features.dropna(axis=0)

    def VolatilityRegime(self, vol_period=10):

        log_return = np.log(self.data['close'] / self.data['close'].shift(1))
        volatility = log_return.ewm(span=vol_period).std()

        features = pd.DataFrame()
        features['volatility'] = volatility * 100
        features['Range'] = 100 * (self.data['high'] - self.data['low']) / self.data['low']
        features['Range_prev_low'] = 100 * (self.data['high'] - self.data['low'].shift(1)) / self.data['low'].shift(1)

        return features

    def generate_features(self):
        params = self.get_params
        self.normalized_features , regime_input= self.TREND_EMA(**params) if self.strategy_name =='TREND_EMA' else(self.SharpeRev(**params) if self.strategy_name == 'SharpeRev' else self.MOM_BURST(**params))

        if self.strategy_name =='TREND_EMA':
            for name in self.Components:
                dt = self.TICKER.get_data(name, f'{self.interval}')
                cmp_params = {'window': params['window'],'normal_window': params['normal_window'], 'lags': params['lags'], 'id_':name}
                normalized_features_cmp = self.TREND_EMA_components(dt, **cmp_params)
                idx = self.normalized_features.index
                self.normalized_features = pd.concat([self.normalized_features, normalized_features_cmp.loc[idx]],axis=1)

    #   setting regimes
        regime = self.Regimer(regime_input)
        self.normalized_features = pd.concat([self.normalized_features, regime], axis=1)

    def TREND_EMA(self, window, lookback_1,lookback_2, normal_window, lags):

        # Initialization of variables
        features = pd.DataFrame()

#       calculating indicator values
        candle_range = self.data['high'] - self.data['low']
        rsi = ta.rsi(self.data['close'], window)
        EMA = self.data['close'].ewm(span=window).mean()
        angle_1 = line_angle(EMA, lookback_1)
        angle_2 = line_angle(EMA, lookback_2)
        zscore = Z_score(EMA, window)

#       calculating strategy components
        features['pct_change'] = self.data['close'].pct_change()
        features['rsi'] = rsi
        features['EMA'] = EMA
        features['spr'] = self.data['close'] / EMA
        features['candle_range'] = candle_range
        features['angle_1'] = angle_1
        features['angle_2'] = angle_2
        features['angle_ratio'] = angle_1 / angle_2
        features['zscore'] = zscore

#       calculating lagged features
        if lags:
            lag_values = pd.DataFrame()
            for col in features.columns:
                for lag in range(1, lags + 1):
                    lag_values[f'{col}_{lag}'] = features[col].shift(lag)
#       concatenate the feature and lag features
            features = pd.concat([features, lag_values], axis=1)

#       normalization the features
        normalized_features = self.Normalization(features, normal_window, True)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        VolatilityRegime = self.VolatilityRegime()
        return normalized_features, VolatilityRegime.loc[normalized_features.index]

    def TREND_EMA_components(self,dt,window, normal_window, lags,id_):
        features = pd.DataFrame()

        # calculating the indicator values
        rsi = ta.rsi(dt['close'], window)
        EMA = dt['close'].ewm(span=window).mean()
        zscore = Z_score(dt['close'], window)

        # setting features
        features['rsi'] = rsi
        features['EMA'] = EMA
        features['zscore'] = zscore
        features['pct_change'] = dt['close'].pct_change()
        features['spr'] = dt['close'] / EMA

        if dt['volume'].mean() > 0:
            # volume based indicators
            average_volume = dt['volume'].rolling(window=window).mean()
            volume_score = (dt['volume'] - average_volume) / average_volume
            vwap = ta.vwap(dt['high'], dt['low'], dt['close'], dt['volume'])
            zscore_volume = Z_score(dt['volume'], window)

        #   setting volume based features
            features['vwap'] = vwap
            features['volume_score'] = volume_score
            features['volume_zscore'] = zscore_volume

        # calculating lagged features
        if lags:
            lag_values = pd.DataFrame()
            for col in features.columns:
                for lag in range(1, lags + 1):
                    lag_values[f'{col}_{lag}'] = features[col].shift(lag)
                    #       concatenate the feature and lag features
            features = pd.concat([features, lag_values], axis=1)

        #       normalization the features
        normalized_features = self.Normalization(features, normal_window, True)
        normalized_features.columns = [f"{col}_{id_}" for col in normalized_features.columns]
        return normalized_features

    def SharpeRev(self,lookback, q_dn,q_up, window, normal_window, lags):
        # Initialization of variables
        features = pd.DataFrame()

        # calculating indicator values
        mean = self.data['close'].pct_change().rolling(window=lookback).mean() * 100
        std = self.data['close'].pct_change().rolling(window=lookback).std() * 100
        pct_change = self.data['close'].pct_change() * 100
        spr = (pct_change - mean) / std
        EMA = self.data['close'].ewm(span=lookback).mean()

        # calculating strategy components(spr , quantiles)
        features['spr'] = spr
        features['quan_up'] = features['spr'].rolling(window=window).quantile(q_up)
        features['quan_dn'] = features['spr'].rolling(window=window).quantile(q_dn)
        features['spr_quan_up'] = features['quan_up'] - features['spr']
        features['spr_quan_dn'] = features['spr'] - features['quan_dn']
        features['sentiment'] = EMA - self.data['close']
        features['pct_change'] = pct_change


        # adding lagged features
        if lags:
            lag_values = pd.DataFrame()
            for col in features.columns:
                for lag in range(1, lags + 1):
                    lag_values[f'{col}_{lag}'] = features[col].shift(lag)
        #   concatenate the feature and lag features
            features = pd.concat([features, lag_values], axis=1)

        # normalization the features
        normalized_features = self.Normalization(features, normal_window, True)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        VolatilityRegime = self.VolatilityRegime()
        return normalized_features, VolatilityRegime.loc[normalized_features.index]

    def MOM_BURST(self,lookback,  normal_window, lags):
        # Initialization of variables
        features = pd.DataFrame()

        # calculating indicator values
        v1, v2 = calculate_MOM_Burst(self.data, lookback)
        candle_range = self.data['high'] - self.data['low']
        rsi = ta.rsi(self.data['close'], lookback)

        # calculating strategy components
        features['mom_burst'] = v1
        features['pct_change'] = self.data['close'].pct_change()
        features['range_mean_vs_candle_range'] = candle_range / v2
        features['mom_burst_hh'] = v1 / v1.rolling(window=lookback).max().shift(1)
        features['mom_burst_ll'] = v1.rolling(window=lookback).min().shift(1) / v1
        features['rsi'] = rsi

        for col in ['range_mean_vs_candle_range', 'mom_burst_hh', 'mom_burst_ll']:
            features[f'{col}_STD'] = features[col].ewm(span=lookback).std()

        # calculating lagged features
        if lags:
            lag_values = pd.DataFrame()
            for col in features.columns:
                for lag in range(1, lags + 1):
                    lag_values[f'{col}_{lag}'] = features[col].shift(lag)
        #   concatenate the feature and lag features
            features = pd.concat([features, lag_values], axis=1)

        # normalization the features
        normalized_features = self.Normalization(features, normal_window, True)
        normalized_features['dayofweek'] = normalized_features.index.dayofweek
        VolatilityRegime = self.VolatilityRegime()
        return normalized_features, VolatilityRegime.loc[normalized_features.index]

    def Regimer(self ,regime_input):
        # Volatility Regime
        states = pd.Series(self.regime_model_1.predict(regime_input),index= regime_input.index , name = 'Regime')
        return states










