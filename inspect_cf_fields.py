import os, requests, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

key = os.environ.get('CURSEFORGE_API_KEY')
headers = {'x-api-key': key, 'Accept': 'application/json'}

# Inspect the first mod (Home, id=1428236) to see ALL available fields
r = requests.get("https://api.curseforge.com/v1/mods/1428236", headers=headers, timeout=15)
data = r.json()['data']

print("=== TOP-LEVEL FIELDS ===")
for k in data.keys():
    v = data[k]
    if isinstance(v, str) and len(v) > 100:
        print(f"  {k}: (string, {len(v)} chars)")
    else:
        print(f"  {k}: {json.dumps(v, ensure_ascii=False)[:200]}")

print("\n=== SCREENSHOTS ===")
print(json.dumps(data.get('screenshots', []), indent=2))

print("\n=== LOGO ===")
print(json.dumps(data.get('logo', {}), indent=2))

print("\n=== SUMMARY / DESCRIPTION ===")
print(f"summary: {data.get('summary', 'N/A')[:500]}")
