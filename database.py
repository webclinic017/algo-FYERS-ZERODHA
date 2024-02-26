import pandas as pd
import requests
from requests.exceptions import Timeout
from datetime import datetime

def request_position():
    records = pd.DataFrame()
    url = 'https://algotrade.pythonanywhere.com/get_position'
    response = requests.get(url)
    if response.json() != 'no records':
        records = pd.DataFrame.from_records(response.json())
    return records

def UpdatePositionBook(Date, entrytime, exittime ,strategy_name, Transtype, Instrument, Signal, NetQty, NAV, POSITION):
    url = 'https://algotrade.pythonanywhere.com/append_position'

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

def get_expiry(Indices):
    input_format = "%d-%b-%Y"
    output_format = "%d%b%y"
    url = f'https://www.nseindia.com/api/option-chain-indices?symbol={Indices}'
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36" }
    records = requests.get(url,headers=headers).json()['records']
    format_exp = [datetime.strptime(date, input_format).strftime(output_format).upper() for date in records['expiryDates']]
    return format_exp