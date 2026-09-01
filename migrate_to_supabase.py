import json
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

supabase: Client = create_client(url, key)

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def migrate():
    data = load_data()
    if not data:
        print("No data.json found or it's empty.")
        return

    print("Starting batched migration...")

    portfolios_to_insert = []
    assets_to_insert = []
    history_to_insert = []
    benchmarks_data_to_insert = []
    benchmarks_hist_to_insert = []
    settings_to_insert = []

    portfolios_data = data.get("portfoliosData", {})
    for month, portfolios in portfolios_data.items():
        for p in portfolios:
            portfolios_to_insert.append({
                "id": p["id"],
                "month": month,
                "name": p["name"],
                "color": p["color"]
            })
            for a in p.get("assets", []):
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

    benchmarks_data_dict = data.get("benchmarksData", {})
    for month, benchmarks in benchmarks_data_dict.items():
        for sym, price in benchmarks.items():
            benchmarks_data_to_insert.append({
                "month": month,
                "symbol": sym,
                "price": price
            })

    benchmarks_history = data.get("benchmarksHistory", {})
    for sym, hist in benchmarks_history.items():
        for date_str, price in hist.items():
            if price is not None:
                benchmarks_hist_to_insert.append({
                    "symbol": sym,
                    "date": date_str,
                    "price": price
                })

    settings_keys = [
        "frozenMonths", "activeBenchmarks", "currentViewMonth", 
        "currentPortfolioId", "monthlyChartType", "deleteQueue",
        "compareTimeRange", "compareChartType"
    ]
    for key in settings_keys:
        if key in data:
            settings_to_insert.append({
                "key": key,
                "value": data[key]
            })

    print(f"Prepared {len(portfolios_to_insert)} portfolios, {len(assets_to_insert)} assets, {len(history_to_insert)} history, {len(benchmarks_data_to_insert)} b_data, {len(benchmarks_hist_to_insert)} b_hist, {len(settings_to_insert)} settings.")

    try:
        if portfolios_to_insert:
            print("Inserting portfolios...")
            supabase.table("portfolios").upsert(portfolios_to_insert).execute()
        if assets_to_insert:
            print("Inserting assets...")
            supabase.table("assets").upsert(assets_to_insert).execute()
        
        # Batch inserting large history can sometimes fail if payload too large. Let's do 1000 items at a time
        if history_to_insert:
            print(f"Inserting {len(history_to_insert)} portfolio history records...")
            for i in range(0, len(history_to_insert), 1000):
                supabase.table("portfolio_history").upsert(history_to_insert[i:i+1000]).execute()
        
        if benchmarks_data_to_insert:
            print("Inserting benchmark data...")
            supabase.table("benchmarks_data").upsert(benchmarks_data_to_insert).execute()
            
        if benchmarks_hist_to_insert:
            print(f"Inserting {len(benchmarks_hist_to_insert)} benchmark history records...")
            for i in range(0, len(benchmarks_hist_to_insert), 1000):
                supabase.table("benchmarks_history").upsert(benchmarks_hist_to_insert[i:i+1000]).execute()
                
        if settings_to_insert:
            print("Inserting settings...")
            supabase.table("settings").upsert(settings_to_insert).execute()
            
        print("Migration completed!")
    except Exception as e:
        print(f"Error during batched insert: {e}")

if __name__ == "__main__":
    migrate()
