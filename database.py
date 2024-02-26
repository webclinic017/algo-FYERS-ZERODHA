import pandas as pd
import requests
from requests.exceptions import Timeout
from datetime import datetime

def request_position():
    records = pd.DataFrame()
    url = 'https://algotrade.pythonanywhere.com/get_position_Intraday'
    response = requests.get(url)
    if response.json() != 'no records':
        records = pd.DataFrame.from_records(response.json())
    return records

def UpdatePositionBook(Date, entrytime, exittime ,strategy_name, Transtype, Instrument, Signal, NetQty, NAV, POSITION):
    url = 'https://algotrade.pythonanywhere.com/append_position_Intraday'

    # creating records
    records = {'Date': Date, 'entrytime': entrytime, 'Strategy': strategy_name, 'Transtype': Transtype,
               'Instrument': Instrument,'Signal': Signal, 'NetQty': NetQty,
               'NAV':  NAV, 'POSITION': POSITION,'exittime':exittime}

    payload = pd.DataFrame.from_dict([records]).to_json(orient='records')
    try:
        response = requests.post(url, json=payload)

    except Timeout:
        print('Timeout:Unable to update the PositionBook Server , Server might be busy')
        print(f'PAYLOAD:{payload}')

def GetOpenPosition(strategy):
    records = pd.DataFrame()
    Open_Pos = request_position()
    if not Open_Pos.empty:
        is_open = (Open_Pos['Strategy'] == strategy) & (Open_Pos['POSITION'] == 'OPEN')
        records = Open_Pos.loc[is_open]
    return records

class NSE_SESSION:
    def __init__(self):
        self.headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
            'accept-language': 'en,gu;q=0.9,hi;q=0.8',
            'accept-encoding': 'gzip, deflate, br'}
        self.cook_url = "https://www.nseindia.com/option-chain"
        self.session = requests.Session()
        self.cookies = self.session.get(self.cook_url, headers=self.headers , timeout = 5).cookies

    def GetExpiry(self,indices):
        url = f'https://www.nseindia.com/api/option-chain-indices?symbol={indices}'
        input_format = "%d-%b-%Y"
        output_format = "%d%b%y"
        try:
            response = self.session.get(url,headers=self.headers, timeout=5, cookies=self.cookies)
            if response.status_code == 200:
                records = response.json()['records']
                format_exp = [datetime.strptime(date, input_format).strftime(output_format).upper() for date in
                              records['expiryDates']]
                return format_exp
            else:
                return []

        except Exception as ex:
            print('Error: {}'.format(ex))