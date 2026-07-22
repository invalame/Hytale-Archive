import os, requests, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

token = os.environ.get('MODIFOLD_API_KEY')
headers = {
    'Authorization': f'Bearer {token}',
    'User-Agent': 'HytaleArchiveBot/1.0 (Contact: pemaidana0@gmail.com)',
    'Accept': 'application/json'
}

slug = "mermaids"

print("=== GET /v2/projects/mermaids ===")
r = requests.get(f"https://api.modifold.com/v2/projects/{slug}", headers=headers, timeout=15)
print(f"HTTP {r.status_code}")
if r.status_code == 200:
    print(json.dumps(r.json(), indent=2)[:2000])

print("\n=== GET /v2/projects/mermaids/versions ===")
r2 = requests.get(f"https://api.modifold.com/v2/projects/{slug}/versions", headers=headers, timeout=15)
print(f"HTTP {r2.status_code}")
if r2.status_code == 200:
    print(json.dumps(r2.json(), indent=2)[:2000])
else:
    print(r2.text[:300])

print("\n=== GET /projects/mermaids/versions (v1) ===")
r3 = requests.get(f"https://api.modifold.com/v1/projects/{slug}/versions", headers=headers, timeout=15)
print(f"HTTP {r3.status_code}")
if r3.status_code == 200:
    print(json.dumps(r3.json(), indent=2)[:2000])
else:
    print(r3.text[:300])
