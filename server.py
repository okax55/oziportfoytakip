import json
import os
import math
import concurrent.futures
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Vercel's read-only filesystem workaround for yfinance
try:
    os.environ['YF_CACHE_DIR'] = '/tmp'
    import yfinance as yf
except Exception as e:
    print("Failed to import yfinance:", e)
    yf = None
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key) if url and key else None

from flask import send_from_directory
app = Flask(__name__, static_folder='.')
CORS(app)

def load_data():
    if not supabase:
        return None
    try:
        data = {}
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            fut_settings = executor.submit(lambda: supabase.table("settings").select("*").execute())
            fut_ports = executor.submit(lambda: supabase.table("portfolios").select("*").execute())
            fut_assets = executor.submit(lambda: supabase.table("assets").select("*").execute())
            fut_hist = executor.submit(lambda: supabase.table("portfolio_history").select("*").execute())
            fut_b_data = executor.submit(lambda: supabase.table("benchmarks_data").select("*").execute())
            fut_b_hist = executor.submit(lambda: supabase.table("benchmarks_history").select("*").execute())

            settings_res = fut_settings.result()
            portfolios_res = fut_ports.result()
            assets_res = fut_assets.result()
            history_res = fut_hist.result()
            b_data_res = fut_b_data.result()
            b_hist_res = fut_b_hist.result()

        for row in settings_res.data:
            data[row["key"]] = row["value"]

        portfolios_data = {}
        for p in portfolios_res.data:
            month = p["month"]
            if month not in portfolios_data:
                portfolios_data[month] = []
            portfolios_data[month].append({
                "id": p["id"],
                "name": p["name"],
                "color": p["color"],
                "assets": [],
                "dailyHistory": {}
            })
            
        for a in assets_res.data:
            for month, ports in portfolios_data.items():
                for p in ports:
                    if p["id"] == a["portfolio_id"]:
                        p["assets"].append({
                            "id": a["id"],
                            "name": a["name"],
                            "amount": a["amount"],
                            "cost": a["cost"],
                            "price": a["price"]
                        })
                        
        for h in history_res.data:
            for month, ports in portfolios_data.items():
                for p in ports:
                    if p["id"] == h["portfolio_id"]:
                        p["dailyHistory"][h["date"]] = h["change_pct"]
                        
        data["portfoliosData"] = portfolios_data
        
        benchmarks_data = {}
        for b in b_data_res.data:
            month = b["month"]
            if month not in benchmarks_data:
                benchmarks_data[month] = {}
            benchmarks_data[month][b["symbol"]] = b["price"]
        data["benchmarksData"] = benchmarks_data
        
        benchmarks_history = {}
        for b in b_hist_res.data:
            sym = b["symbol"]
            if sym not in benchmarks_history:
                benchmarks_history[sym] = {}
            benchmarks_history[sym][b["date"]] = b["price"]
        data["benchmarksHistory"] = benchmarks_history
        
        if not portfolios_data:
            return None
            
        return data
    except Exception as e:
        print("Error loading data from Supabase:", e)
        return None

def save_data(data):
    if not supabase:
        return
    try:
        incoming_p_ids = []
        incoming_a_ids = []
        
        portfolios_to_insert = []
        assets_to_insert = []
        history_to_insert = []
        
        for month, portfolios in data.get("portfoliosData", {}).items():
            for p in portfolios:
                incoming_p_ids.append(p["id"])
                portfolios_to_insert.append({
                    "id": p["id"],
                    "month": month,
                    "name": p["name"],
                    "color": p["color"]
                })
                for a in p.get("assets", []):
                    incoming_a_ids.append(a["id"])
                    assets_to_insert.append({
                        "id": a["id"],
                        "portfolio_id": p["id"],
                        "name": a["name"],
                        "amount": a["amount"],
                        "cost": a["cost"],
                        "price": a.get("price", a["cost"])
                    })
                for date_str, change in p.get("dailyHistory", {}).items():
                    history_to_insert.append({
                        "portfolio_id": p["id"],
                        "date": date_str,
                        "change_pct": change
                    })
        
        if portfolios_to_insert:
            supabase.table("portfolios").upsert(portfolios_to_insert).execute()
            
        if incoming_p_ids:
            existing_p = supabase.table("portfolios").select("id").execute()
            to_delete_p = set([row["id"] for row in existing_p.data]) - set(incoming_p_ids)
            if to_delete_p:
                supabase.table("portfolios").delete().in_("id", list(to_delete_p)).execute()
                
        if assets_to_insert:
            supabase.table("assets").upsert(assets_to_insert).execute()
            
        if incoming_a_ids:
            existing_a = supabase.table("assets").select("id").execute()
            to_delete_a = set([row["id"] for row in existing_a.data]) - set(incoming_a_ids)
            if to_delete_a:
                supabase.table("assets").delete().in_("id", list(to_delete_a)).execute()
                
        if history_to_insert:
            for i in range(0, len(history_to_insert), 1000):
                supabase.table("portfolio_history").upsert(history_to_insert[i:i+1000]).execute()

        b_data_insert = []
        for month, benchmarks in data.get("benchmarksData", {}).items():
            for sym, price in benchmarks.items():
                b_data_insert.append({"month": month, "symbol": sym, "price": price})
        if b_data_insert:
            supabase.table("benchmarks_data").upsert(b_data_insert).execute()

        b_hist_insert = []
        for sym, hist in data.get("benchmarksHistory", {}).items():
            for date_str, price in hist.items():
                if price is not None:
                    b_hist_insert.append({"symbol": sym, "date": date_str, "price": price})
        if b_hist_insert:
            for i in range(0, len(b_hist_insert), 1000):
                supabase.table("benchmarks_history").upsert(b_hist_insert[i:i+1000]).execute()

        settings_keys = [
            "frozenMonths", "activeBenchmarks", "currentViewMonth", 
            "currentPortfolioId", "monthlyChartType", "deleteQueue",
            "compareTimeRange", "compareChartType"
        ]
        settings_insert = []
        for key in settings_keys:
            if key in data:
                settings_insert.append({"key": key, "value": data[key]})
        if settings_insert:
            supabase.table("settings").upsert(settings_insert).execute()

    except Exception as e:
        print("Error saving data to Supabase:", e)

@app.route('/api/load', methods=['GET'])
@app.route('/load', methods=['GET'])
def api_load():
    data = load_data()
    if data is None:
        return jsonify({"status": "empty", "data": {}})
    return jsonify({"status": "success", "data": data})

@app.route('/api/save', methods=['POST'])
@app.route('/save', methods=['POST'])
def api_save():
    data = request.json
    save_data(data)
    return jsonify({"status": "success"})

@app.route('/api/prices', methods=['POST'])
@app.route('/prices', methods=['POST'])
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
    if "NASDAQ" in fetch_symbols:
        fetch_symbols.remove("NASDAQ")
        fetch_symbols.add("^IXIC")
    if "SP500" in fetch_symbols:
        fetch_symbols.remove("SP500")
        fetch_symbols.add("^GSPC")
        
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
                        last_price = float(hist['Close'].iloc[-1])
                        if not math.isnan(last_price):
                            results[sym] = last_price
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
            
    if "NASDAQ" in symbols:
        val = results.get("^IXIC")
        if val: results["NASDAQ"] = val
    if "SP500" in symbols:
        val = results.get("^GSPC")
        if val: results["SP500"] = val

    return jsonify({"status": "success", "prices": results})

@app.route('/api/history', methods=['POST'])
def api_history():
    """
    Beklenen girdi: {"symbols": ["THYAO.IS", "TUPRS.IS", "XU100.IS", "ALTIN"], "period": "1mo"}
    """
    req_data = request.json
    symbols = req_data.get('symbols', [])
    period = req_data.get('period', '1mo')
    
    fetch_symbols = set(symbols)
    if "ALTIN" in fetch_symbols:
        fetch_symbols.remove("ALTIN")
        fetch_symbols.add("GC=F")
        fetch_symbols.add("TRY=X")
    if "NASDAQ" in fetch_symbols:
        fetch_symbols.remove("NASDAQ")
        fetch_symbols.add("^IXIC")
    if "SP500" in fetch_symbols:
        fetch_symbols.remove("SP500")
        fetch_symbols.add("^GSPC")
        
    results = {}
    if fetch_symbols:
        try:
            tickers = yf.Tickers(" ".join(fetch_symbols))
            for sym in fetch_symbols:
                try:
                    hist = tickers.tickers[sym].history(period=period)
                    if not hist.empty:
                        if hist.index.tz is not None:
                            hist.index = hist.index.tz_localize(None)
                        dates = hist.index.strftime('%Y-%m-%d').tolist()
                        closes = [None if math.isnan(x) else x for x in hist['Close'].tolist()]
                        results[sym] = dict(zip(dates, closes))
                except Exception as e:
                    print(f"Hata: {sym} gecmis fiyatı alınamadı. {e}")
        except Exception as e:
            print(f"yfinance genel hatası: {e}")

    # Altın için geçmiş fiyatları hesapla
    if "ALTIN" in symbols:
        ons_hist = results.get("GC=F", {})
        usd_try_hist = results.get("TRY=X", {})
        altin_hist = {}
        for date, ons_price in ons_hist.items():
            usd_price = usd_try_hist.get(date)
            if usd_price:
                altin_hist[date] = (ons_price * usd_price) / 31.1034768
        if altin_hist:
            results["ALTIN"] = altin_hist

    if "NASDAQ" in symbols:
        hist = results.get("^IXIC")
        if hist: results["NASDAQ"] = hist
    if "SP500" in symbols:
        hist = results.get("^GSPC")
        if hist: results["SP500"] = hist

    return jsonify({"status": "success", "history": results})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/logo.png')
def serve_logo():
    return send_from_directory('.', 'logo.png')

if __name__ == '__main__':
    print("Ozi Portföy Backend çalışıyor: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
