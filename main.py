import pandas as pd
from flask import Flask, render_template,jsonify ,request ,send_file
import numpy as np
import random
from database import post_position , request_position,append_position
import io

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/update-tick-data')
def update_tick_data():
    # Simulated function to fetch new tick data (replace with actual API calls)
    # In this example, we simply return the same simulated data for demonstration purposes
    updated_data = {
        'banknifty': np.random.randint(35000,44500),
        'nifty':  np.random.randint(18000,20000),
        'finnifty':  np.random.randint(18000,19000),
    }
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
