import pandas as pd
import requests
from requests.exceptions import Timeout
PositionBook = pd.DataFrame()

def request_position():
    global PositionBook
    url = 'https://algotrade.pythonanywhere.com/get_position'
    response = requests.get(url)
    if response.json()!='no records found':
       PositionBook = pd.DataFrame.from_records(response.json())
       return PositionBook

def append_position(Date ,entrytime  ,exittime, Strategy , Transtype ,Instrument , ABP , ASP ,Qty , BuyValue , SellValue, MTM):
    global PositionBook
    trade_detail = {'Date': Date,
            'entrytime':entrytime,
            'exittime':exittime,
            'Strategy': Strategy,
            'Transtype': Transtype,
            'Instrument': Instrument,
            'ABP': ABP,
            'ASP': ASP,
            'Qty': Qty,
            'AverageBuyValue':BuyValue,
            'AverageSellValue':SellValue,
            'MTM': MTM
             }

    PositionBook = pd.DataFrame.from_dict([trade_detail])


def post_position():
    url = 'https://algotrade.pythonanywhere.com/append_position'
    global PositionBook
    payload = PositionBook.to_json(orient='records')
    try:
        response = requests.post(url, json=payload)

    except Timeout:
        print('Timeout:Unable to update the PositionBook Server , Server might be busy')
        print(f'PositionNotUpdated:{PositionBook.iloc[-1]}')
