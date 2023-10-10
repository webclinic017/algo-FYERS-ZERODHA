from flask import Flask, render_template ,jsonify
import numpy as np

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

