import pandas as pd
import requests
from requests.exceptions import Timeout


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