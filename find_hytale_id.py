import urllib.request
import urllib.error
import json
import os

key = os.environ.get('CURSEFORGE_API_KEY', '5f72b6b4-bf34-41fd-a257-df95a7b24f89')
url = 'https://api.curseforge.com/v1/games'
req = urllib.request.Request(url, headers={'x-api-key': key, 'Accept': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        games = data.get('data', [])
        print(f"Found {len(games)} games.")
        found = False
        for game in games:
            if game.get('slug') == 'hytale' or game.get('name').lower() == 'hytale':
                print(f"[SUCCESS] Hytale found! gameId: {game.get('id')}, name: {game.get('name')}")
                found = True
                break
        if not found:
            print("[WARN] Hytale not found in CurseForge games list.")
            print("First 3 games:", [g.get('name') for g in games[:3]])
except urllib.error.HTTPError as e:
    print(f"[ERROR] HTTP Error {e.code}: {e.reason}")
    if e.code == 403:
        print("Note: API key might be invalid or revoked.")
except Exception as e:
    print(f"[ERROR] {e}")
