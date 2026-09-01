import server
import json

data = server.load_data()
with open("test_load.json", "w") as f:
    json.dump(data, f, indent=2)
print("Keys in data:", data.keys())
print("Portfolios:", data.get("portfoliosData", {}).keys())
