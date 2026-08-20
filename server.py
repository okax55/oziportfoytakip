import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf

from flask import send_from_directory
app = Flask(__name__, static_folder='.')
CORS(app)

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return None
    return None

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/api/load', methods=['GET'])
def api_load():
    data = load_data()
    if data is None:
        return jsonify({"status": "empty", "data": {}})
    return jsonify({"status": "success", "data": data})

@app.route('/api/save', methods=['POST'])
def api_save():
    data = request.json
    save_data(data)
    return jsonify({"status": "success"})

@app.route('/api/prices', methods=['POST'])
def api_prices():
    """
    Beklenen girdi: {"symbols": ["THYAO.IS", "TUPRS.IS", "XU100.IS", "ALTIN"]}
    """
    req_data = request.json
    symbols = req_data.get('symbols', [])
    
    # Altın için özel semboller: GC=F (Ons Altın) ve TRY=X (Dolar/TL)
    fetch_symbols = set(symbols)
    if "ALTIN" in fetch_symbols:
        fetch_symbols.remove("ALTIN")
        fetch_symbols.add("GC=F")
        fetch_symbols.add("TRY=X")
        
    results = {}
    if fetch_symbols:
        try:
            # yfinance ile çoklu sembol çekimi
            tickers = yf.Tickers(" ".join(fetch_symbols))
            for sym in fetch_symbols:
                try:
                    # history(period="1d") genellikle en son kapanışı/anlık fiyatı verir
                    hist = tickers.tickers[sym].history(period="1d")
                    if not hist.empty:
                        last_price = hist['Close'].iloc[-1]
                        results[sym] = float(last_price)
                except Exception as e:
                    print(f"Hata: {sym} fiyatı alınamadı. {e}")
        except Exception as e:
            print(f"yfinance genel hatası: {e}")

    # Altın fiyatını hesapla (Gram Altın = Ons * USDTRY / 31.103)
    if "ALTIN" in symbols:
        ons = results.get("GC=F")
        usd_try = results.get("TRY=X")
        if ons and usd_try:
            gram_altin = (ons * usd_try) / 31.1034768
            results["ALTIN"] = gram_altin

    return jsonify({"status": "success", "prices": results})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    print("Ozi Portföy Backend çalışıyor: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
