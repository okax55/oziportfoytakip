import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
print(f"Connecting to {url}...")
try:
    supabase: Client = create_client(url, key)
    print("Client created. Fetching from settings...")
    res = supabase.table("settings").select("*").execute()
    print("Fetch successful:", res.data)
except Exception as e:
    print("Error:", e)
