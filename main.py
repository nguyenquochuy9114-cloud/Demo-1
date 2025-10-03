from flask import Flask, render_template
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=30"
        response = requests.get(url).json()
        df = pd.DataFrame(response["prices"], columns=["time", "price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time"], y=df["price"], name="BTC Price"))
        fig.update_layout(template="plotly_dark")

        plot_html = fig.to_html(full_html=False)

        latest = df.iloc[-1]
        return render_template("index.html",
                               time=datetime.now().strftime("%Y-%m-%d %H:%M"),
                               price=f"${latest['price']:.2f}",
                               plot=plot_html)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
