from datetime import datetime , timedelta
import pandas as pd
import schedule

class TICKER_():
    BROKER_OBJ = None
    STRATEGY_RUN = None

    def __init__(self , ticker):
        self.ticker_under_strategy = ticker
        self.ticker_space = {}
        self.scheduler = schedule.Scheduler()
        self.update_tag=False

    def get_history(self ,symbol, interval, days = 4 ):
        range_to = datetime.now().date()
        range_from = range_to - timedelta(days=days)
        req = {"symbol": symbol, "resolution": f"{interval}", "date_format": "1", "range_from": str(range_from),
               "range_to": str(range_to), "cont_flag": "1"}
        his = self.BROKER_OBJ.history(req)['candles']
        self.hist_df = pd.DataFrame(his, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.hist_df['timestamp'] = pd.to_datetime(self.hist_df['timestamp'],unit='s')
        self.hist_df['timestamp'] = self.hist_df['timestamp'].dt.tz_localize('utc').dt.tz_convert('Asia/Kolkata')
        self.hist_df['timestamp'] = self.hist_df['timestamp'].dt.tz_localize(None)
        self.hist_df = self.hist_df.set_index('timestamp')
        return self.hist_df

    def run_update(self):
            for ticker,interval in self.ticker_under_strategy.items():
                self.ticker_space[f"{ticker}_{interval}"] = self.get_history(ticker,interval)

            for strategy in self.STRATEGY_RUN.keys():
                self.STRATEGY_RUN[strategy].monitor_signal(self.ticker_space)


    def run_scheduler(self):
        if not self.scheduler.jobs:
            now = datetime.now()
            for interval in self.ticker_under_strategy.values():
                if now.minute % interval == 0 and now.second > 5 and now.second < 8:
                    self.scheduler.every(interval).minutes.do(self.run_update)
                    print(f'task scheduled :{self.scheduler.jobs}')


        self.scheduler.run_pending()




    def get_data(self ,symbol):
        try:
           return self.ticker_space[symbol]
        except KeyError:
            return pd.DataFrame()







