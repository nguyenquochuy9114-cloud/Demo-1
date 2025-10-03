from flask import Flask, render_template, request
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

app = Flask(__name__)

# Trang chủ: chọn coin
@app.route('/')
def home():
    # Lấy danh sách top 300 coin từ CoinGecko
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 300, "page": 1}
    coins = requests.get(url, params=params).json()

    return render_template("index.html", coins=coins, chart=None)


# Trang phân tích 1 coin
@app.route('/analyze/<coin_id>')
def analyze(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=30"
        response = requests.get(url).json()

        df = pd.DataFrame(response["prices"], columns=["time", "price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df = df.merge(pd.DataFrame(response["total_volumes"], columns=["time", "volume"]), on="time", how="left")
        df = df.merge(pd.DataFrame(response["market_caps"], columns=["time", "market_cap"]), on="time", how="left")

        # Tính inflow, outflow
        df["price_change"] = df["price"].pct_change().fillna(0)
        df["inflow"] = np.where(df["price_change"] > 0, df["price"] * df["price_change"], 0)
        df["outflow"] = np.where(df["price_change"] < 0, df["price"] * abs(df["price_change"]), 0)
        df["volume_percent_mc"] = (df["volume"] / df["market_cap"]).fillna(0) * 100

        # RSI
        delta = df["price"].diff().fillna(0)
        gain = delta.where(delta > 0, 0).rolling(window=14, min_periods=1).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14, min_periods=1).mean()
        rs = gain / loss.replace(0, np.finfo(float).eps)
        df["RSI"] = 100 - (100 / (1 + rs)).fillna(50)

        # MACD
        exp1 = df["price"].ewm(span=12, min_periods=1).mean()
        exp2 = df["price"].ewm(span=26, min_periods=1).mean()
        macd = exp1 - exp2
        df["MACD"] = macd.fillna(0)
        df["MACD_signal"] = macd.ewm(span=9, min_periods=1).mean().fillna(0)
        df["signal"] = np.where((df["RSI"] < 30) & (df["MACD"] > df["MACD_signal"]), "Buy",
                               np.where((df["RSI"] > 70) & (df["MACD"] < df["MACD_signal"]), "Sell", "Hold"))

        # Volume ratio 7/30
        vol_7d = df["volume"].tail(7).mean()
        vol_30d = df["volume"].mean()
        vol_ratio = vol_7d / vol_30d if vol_30d > 0 else 0

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time"], y=df["price"], name="Price", line=dict(color="lime")))
        fig.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI", line=dict(color="magenta")))
        fig.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD", line=dict(color="blue")))
        fig.add_trace(go.Scatter(x=df["time"], y=df["MACD_signal"], name="MACD Signal", line=dict(color="red")))
        fig.update_layout(title=f"{coin_id.upper()} Analysis", xaxis_title="Time", yaxis_title="Value",
                          height=600, template="plotly_dark")
        plot_div = fig.to_html(full_html=False)

        latest_data = df.iloc[-1].fillna(0)
        return render_template("index.html",
                               coins=[],
                               chart=plot_div,
                               price=f"${latest_data['price']:,.2f}",
                               market_cap=f"${latest_data['market_cap']:,.0f}",
                               vol_percent=f"{latest_data['volume_percent_mc']:.2f}%",
                               inflow=f"${df['inflow'].sum():,.0f}",
                               outflow=f"${df['outflow'].sum():,.0f}",
                               vol_ratio=f"{vol_ratio:.2f}",
                               signal=latest_data["signal"],
                               time=datetime.now().strftime("%Y-%m-%d %H:%M"))
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
