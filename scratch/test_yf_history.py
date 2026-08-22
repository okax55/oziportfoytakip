import yfinance as yf
import json

symbols = ["THYAO.IS", "TUPRS.IS"]
tickers = yf.Tickers(" ".join(symbols))
results = {}

for sym in symbols:
    hist = tickers.tickers[sym].history(period="1mo")
    if not hist.empty:
        # hist is a DataFrame with DatetimeIndex
        # convert to string dates "YYYY-MM-DD"
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        closes = hist['Close'].tolist()
        results[sym] = dict(zip(dates, closes))

print(json.dumps(results, indent=4))
