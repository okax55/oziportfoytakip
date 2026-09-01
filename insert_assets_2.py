from server import load_data, supabase
data = load_data()
ports_08 = data['portfoliosData']['2026-08']

import copy
assets_to_insert = []
for p in ports_08:
    new_p_id = p['id'].split('_')[0] + '_202609'
    for a in p['assets']:
        new_a_id = a['id'].split('_')[0] + '_202609'
        assets_to_insert.append({
            "id": new_a_id,
            "portfolio_id": new_p_id,
            "name": a["name"],
            "amount": a["amount"],
            "cost": a.get("price", a["cost"]), # The user wanted September to transition with closing prices
            "price": a.get("price", a["cost"])
        })

print(f"Attempting to insert {len(assets_to_insert)} assets...")
try:
    res = supabase.table("assets").upsert(assets_to_insert).execute()
    print("Success! inserted assets for September.")
except Exception as e:
    print("Error:", e)
