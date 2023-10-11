from flask import Flask, render_template,jsonify
import numpy as np
import random

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




if __name__ == '__main__':
    app.run(debug=True)
