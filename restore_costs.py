import json
from server import supabase

# 1. Load original costs from data.json
with open('data.json', 'r', encoding='utf-8') as f:
    data_json = json.load(f)

original_costs = {}
for p in data_json.get('portfoliosData', {}).get('2026-08', []):
    for a in p.get('assets', []):
        base_id = a['id'].split('_')[0]
        original_costs[base_id] = a['cost']

# 2. Fetch all assets from DB
res_aug = supabase.table('assets').select('*').not_.like('id', '%_202609').execute()
res_sep = supabase.table('assets').select('*').like('id', '%_202609').execute()

# 3. Get August closing prices from DB
aug_closing_prices = {}
for a in res_aug.data:
    base_id = a['id'].split('_')[0]
    aug_closing_prices[base_id] = a['price']

# 4. Prepare updates for August (restore original costs)
updates_aug = []
for a in res_aug.data:
    base_id = a['id'].split('_')[0]
    if base_id in original_costs:
        a['cost'] = original_costs[base_id]
        updates_aug.append(a)

# 5. Prepare updates for September (set cost = August closing prices)
updates_sep = []
for a in res_sep.data:
    base_id = a['id'].split('_')[0]
    if base_id in aug_closing_prices:
        a['cost'] = aug_closing_prices[base_id]
        updates_sep.append(a)

# 6. Push to DB
if updates_aug:
    supabase.table('assets').upsert(updates_aug).execute()
    print("August costs restored successfully!")

if updates_sep:
    supabase.table('assets').upsert(updates_sep).execute()
    print("September costs updated to August closing prices successfully!")
