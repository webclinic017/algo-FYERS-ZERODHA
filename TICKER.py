from datetime import datetime,timedelta
import pandas as pd
import pytz
import time

class TICKER_:
    BROKER_OBJ = None
    STRATEGY_RUN = None
    LIVE_FEED = None

    def __init__(self, ticker):
        self.update_freq = 5
        self.request_retry = 3
        self.ticker_under_strategy = ticker
        self.time_zone = pytz.timezone('Asia/Kolkata')
        self.ticker_space = {}
        self.update_tag = False
        self.last_execution = 0
        self.hist_df = None

    def get_history(self, symbol, interval, days=15):

        # reinitializing the variables
        his = []
        self.hist_df = pd.DataFrame()

        range_to = datetime.now(self.time_zone).date()
        range_from = range_to - timedelta(days=days)
        req = {"symbol": symbol, "resolution": f"{interval}", "date_format": "1", "range_from": str(range_from),
               "range_to": str(range_to), "cont_flag": "1"}
        try:
            his = self.BROKER_OBJ.history(req)['candles']
        except KeyError:
            retry_count = 0
            while retry_count <= self.request_retry:
                resp = self.BROKER_OBJ.history(req)
                if 'candles' in resp:
                    his = resp['candles']
                    break
                else:
                    print('Unable to fetch historical data retrying  in few seconds')
                    time.sleep(2)
                    retry_count += 1

            else:
                print('Unable to fetch the data please check your connections and verify with the broker')

        if his:
            self.hist_df = pd.DataFrame(his, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            self.hist_df['timestamp'] = pd.to_datetime(self.hist_df['timestamp'], unit='s')
            self.hist_df['timestamp'] = self.hist_df['timestamp'].dt.tz_localize('utc').dt.tz_convert('Asia/Kolkata')
            self.hist_df['timestamp'] = self.hist_df['timestamp'].dt.tz_localize(None)
            self.hist_df = self.hist_df.set_index('timestamp')
        return self.hist_df

    def run_update(self):
        print(f'run update:{datetime.now(self.time_zone)}')

        for ticker,interval in self.ticker_under_strategy.items():
            hist = self.get_history(ticker,interval)
            if not hist.empty:
                self.ticker_space[f"{ticker}"] = hist

        for strategy in self.STRATEGY_RUN.keys():
            self.STRATEGY_RUN[strategy].monitor_signal()

    def run_scheduler(self):
        current_minute = int(time.time())
        now = datetime.now(self.time_zone)
        if (now.minute % self.update_freq == 0) and (now.second > 5) and (now.second < 8):
            if (current_minute - self.last_execution) >= 300:
                self.run_update()
                self.last_execution = current_minute

    def get_data(self,symbol,interval):
        try:
            resample = self.ticker_space[symbol].resample(f'{interval}', origin='2017-01-02 09:15').agg(
                    {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
            return resample.iloc[:-1]
        except KeyError:
            return pd.DataFrame()


