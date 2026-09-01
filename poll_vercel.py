import urllib.request
import urllib.error
import time

url = "https://oziportfoytakip.vercel.app/api/load"
print("Waiting for Vercel deployment...")

for _ in range(30):
    try:
        response = urllib.request.urlopen(url)
        content = response.read().decode('utf-8')
        print("Success! Response starts with:")
        print(content[:500])
        break
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(2)
