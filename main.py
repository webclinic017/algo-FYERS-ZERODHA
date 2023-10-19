import pandas as pd
from flask import Flask, render_template,jsonify,request,send_file
from database import request_position
import io
from Broker_api import BROKER_API
from TICKER import TICKER_
from strategy import StrategyFactory
import requests
import warnings as ws
ws.simplefilter('ignore')

connected = 'not connected'
BROKER_APP = False
STRATEGY_FAC = {}
STRATEGY = {}
SELECTED_STRATEGY = {}
wake_up_url  ='https://algotrade.pythonanywhere.com/wake_up'

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/on_connect', methods=['POST'])
def connect():
    global STRATEGY
    global connected
    global BROKER_APP
    global STRATEGY_FAC
    global SELECTED_STRATEGY

    # creating a broker object  after login
    BROKER_APP = BROKER_API()
    BROKER_APP.login()
    BROKER_APP.BROKER_WEBSOCKET_INT()

    # TICKER and interval  used  in strategies
    TICKER_UNDER_STRATEGY = {'NSE:NIFTY50-INDEX':1}
    TICKER_.BROKER_OBJ = BROKER_APP.BROKER_APP
    TICK = TICKER_(TICKER_UNDER_STRATEGY)
    BROKER_API.TICKER_OBJ = TICK

    # setting and creating strategy obj
    StrategyFactory.TICKER_OBJ = TICK
    StrategyFactory.LIVE_FEED = BROKER_APP

    # selecting strategy which is selected with checkbox
    STRATEGY = {'3EMA': {'mode': 'Simulator', 'ticker': 'NSE:NIFTY50-INDEX', 'interval': 1}}
    json = request.get_json()
    SELECTED_STRATEGY = json['selected_strategy']


    for key, value in STRATEGY.items():
        if SELECTED_STRATEGY[key]:
            STRATEGY_FAC[key] = StrategyFactory(key, value['mode'],
            value['ticker'], value['interval'] ,expiry=json['expiry'][value['ticker']])

    BROKER_APP.STRATEGY_RUN = STRATEGY_FAC
    TICKER_.STRATEGY_RUN = STRATEGY_FAC

    requests.get(wake_up_url)

    connected = 'connected'
    return connected


@app.route('/update-tick-data')
def update_tick_data():
    global BROKER_APP

    ticker = ["NSE:NIFTYBANK-INDEX","NSE:NIFTY50-INDEX",'NSE:FINNIFTY-INDEX']

    if BROKER_APP and all([s in BROKER_APP.ltp.keys() for s in ticker]):
        updated_data = {
            'banknifty': BROKER_APP.ltp["NSE:NIFTYBANK-INDEX"],
            'nifty':     BROKER_APP.ltp["NSE:NIFTY50-INDEX"],
            'finnifty':  BROKER_APP.ltp['NSE:FINNIFTY-INDEX'],
        }
    else:
        updated_data = {
            'banknifty': 0,
            'nifty': 0,
            'finnifty': 0}

    return jsonify(updated_data)

@app.route('/update_positions', methods=['GET'])
def update_positions():
    json = {}
    global STRATEGY_FAC
    global STRATEGY
    global SELECTED_STRATEGY
    POSITION = 0

    for strategy in STRATEGY.keys():
        if STRATEGY_FAC:
            value = round(STRATEGY_FAC[strategy].STR_MTM, 2)
            POSITION  = STRATEGY_FAC[strategy].position
        else:
            value = 0
        json[strategy] = {
        'STRATEGY_NAME': strategy,
        'STATUS': 'LIVE' if SELECTED_STRATEGY[strategy] else 'OFFLINE',
        'POSITION': f'OPEN:{POSITION}' if POSITION else 'CLOSED',
        'MTM': value,
        }

    return jsonify(json)


@app.route('/get_csv', methods=['POST'])
def get_csv():
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    df = request_position()

    # Convert the 'Date' column to datetime
    df['Date'] = pd.to_datetime(df['Date'])

    # Filter the data based on the date range
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_data = df[mask]

    # Format the 'entrytime' and 'exittime' columns to include milliseconds
    filtered_data['entrytime'] = pd.to_datetime(filtered_data['entrytime']).dt.strftime('%H:%M:%S')
    filtered_data['exittime'] = pd.to_datetime(filtered_data['exittime']).dt.strftime('%H:%M:%S')

    # Generate the CSV
    csv_data = filtered_data.to_csv(index=False)

    # Return the CSV as an attachment
    return send_file(
        io.BytesIO(csv_data.encode('utf-8')),
        as_attachment=True,
        download_name='filtered_data.csv',
        mimetype='text/csv'
    )
@app.route('/get_connection_status')
def get_connection_status():
    return connected

@app.route('/Square_off_Position' ,methods  = ['POST'])
def Sqaure_off_Position():
    resp = 'POSITION NOT AVAILABLE'
    global STRATEGY_FAC
    selected_str = request.form.get('Square_off_strategy')
    if selected_str in STRATEGY_FAC.keys():
        if STRATEGY_FAC[selected_str].position:
            STRATEGY_FAC[selected_str].squaring_of_all_position_AT_ONCE()
            if not STRATEGY_FAC[selected_str].position:
                resp = 'success'
            else:
                resp = 'Failed'
    return resp


if __name__ == '__main__':
    app.run(debug=True)
