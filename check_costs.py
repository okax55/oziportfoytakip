from server import supabase
res = supabase.table('assets').select('*').like('id', '%_202609').execute()
res8 = supabase.table('assets').select('*').not_.like('id', '%_202609').execute()
print('August Assets:')
for a in res8.data:
    print(f"{a['name']}: cost={a['cost']}, price={a['price']}")
print('\nSeptember Assets:')
for a in res.data:
    print(f"{a['name']}: cost={a['cost']}, price={a['price']}")
