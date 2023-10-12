import pandas as pd
from flask import Flask, render_template,jsonify ,request ,send_file
import numpy as np
import random
from database import post_position , request_position,append_position
import io
from Broker_api import login , BROKER_WEBSOCKET_INT ,  get_ltp

connected = 'not connected'
BROKER_SOCKET  = None


app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/on_connect', methods=['POST'])
def connect():
    global connected
    global BROKER_SOCKET
    login()
    BROKER_SOCKET = BROKER_WEBSOCKET_INT()
    BROKER_SOCKET.connect()
    connected = 'connected'
    return connected


@app.route('/update-tick-data')
def update_tick_data():
    ltp = get_ltp()
    if ltp:
        updated_data = {
            'banknifty': ltp["NSE:NIFTYBANK-INDEX"],
            'nifty':     ltp["NSE:NIFTY50-INDEX"],
            'finnifty':  ltp['NSE:FINNIFTY-INDEX'],
        }
    else:
        updated_data = {
            'banknifty': 0,
            'nifty': 0,
            'finnifty': 0}

    return jsonify(updated_data)

@app.route('/update_positions', methods=['GET'])
def update_positions():
    data = {
        'STRATEGY_EMA': '3EMA',
        'STATUS_EMA': 'LIVE',
        'POSITION_EMA': 'OPEN',
        'MTM_EMA': round(random.uniform(100, 200),2),
        'STRATEGY_RSI': 'RSI',
        'STATUS_RSI': 'OFFLINE',
        'POSITION_RSI': 'CLOSED',
        'MTM_RSI': round(random.uniform(100, 200), 2),

    }


    return jsonify(data)

@app.route('/get_csv', methods = ['POST'])
def get_csv():
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    df = request_position()
    df['Date'] = pd.to_datetime(df['Date'])
    df.index = df['Date']
    mask = (df.index >= start_date) & (df.index <= end_date)
    filtered_data = df.loc[mask]
    csv_data = filtered_data.to_csv(index=False)
    return send_file(
        io.BytesIO(csv_data.encode('utf-8')),
        as_attachment=True,
        download_name='filtered_data.csv',
        mimetype='text/csv'
    )




if __name__ == '__main__':
    app.run(debug=True)
