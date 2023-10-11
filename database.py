import pandas as pd
import requests

PositionBook = pd.DataFrame()

def request_position():
    global PositionBook
    url = 'https://algotrade.pythonanywhere.com/get_position'
    response = requests.get(url)
    if response.json()!='no records found':
       PositionBook = pd.DataFrame.from_records(response.json())
       return PositionBook




def append_position():
    global PositionBook
    trade_detail = {'Date': '2023-08-03 15:15:29',
            'Strategy': '3EMA',
            'Index': 'BANKNIFTY',
            'Instrument': 'BANKNIFTY10AUG23C44500',
            'ABP': '470',
            'ASP': '500',
            'Qty': '100',
            'MTM': '24500',
            'CumulativeMTM': '24500'}

    temp = pd.DataFrame.from_dict([trade_detail])
    PositionBook = pd.concat([PositionBook,temp],axis=0)


def post_position():
    url = 'https://algotrade.pythonanywhere.com/append_position'
    global PositionBook
    payload = PositionBook.to_json(orient='records')
    response = requests.post(url, json=payload)








