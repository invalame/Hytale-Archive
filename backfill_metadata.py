"""
backfill_metadata.py — One-time script to fetch missing metadata for existing mods.

This script fetches:
1. summary (description_short)
2. logo_url
3. screenshots (saves to mod_screenshots table)
4. description (full HTML)

It optimizes API calls by:
- Fetching general info in bulk (POST /v1/mods) -> 1 call per 50 mods
- Fetching full descriptions sequentially (GET /v1/mods/{id}/description) -> 1 call per mod
This guarantees we fetch all 4 fields for a mod with ~1.02 requests per mod.

Usage: python backfill_metadata.py
"""
import os
import sys
import time
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH      = os.path.join(os.path.dirname(__file__), 'archivo_hytale.db')
API_BASE     = "https://api.curseforge.com/v1"
API_KEY      = os.environ.get('CURSEFORGE_API_KEY')
DELAY_S      = 2.0
USER_AGENT   = "HytaleArchiveBot/1.0 (Contact: pemaidana0@gmail.com)"

def get_headers():
    return {
        'x-api-key':    API_KEY,
        'User-Agent':   USER_AGENT,
        'Accept':       'application/json',
        'Content-Type': 'application/json'
    }

def fetch_bulk_metadata(mod_ids):
    """Fetch mod objects in bulk."""
    if not mod_ids:
        return {}
    
    url = f"{API_BASE}/mods"
    payload = {"modIds": mod_ids}
    resp = requests.post(url, headers=get_headers(), json=payload, timeout=15)
    
    if resp.status_code == 200:
        data = resp.json().get('data', [])
        return {str(mod['id']): mod for mod in data}
    return {}

def fetch_description(external_id):
    """Fetch the full HTML description for a single mod."""
    url  = f"{API_BASE}/mods/{external_id}/description"
    resp = requests.get(url, headers=get_headers(), timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        return data.get('data', '')   # HTML string
    return None

def process_chunk(conn, chunk):
    # 1. Fetch bulk info
    external_ids = [int(r['external_id']) for r in chunk]
    print(f"  -> Bulk fetching {len(external_ids)} mods...")
    time.sleep(DELAY_S)
    bulk_data = fetch_bulk_metadata(external_ids)

    # 2. Process each mod
    ok, fail = 0, 0
    for row in chunk:
        mod_id = row['mod_id']
        ext_id = str(row['external_id'])
        title  = row['title']

        print(f"     [+] {title} ({ext_id})...", end=' ', flush=True)

        try:
            # Extract from bulk response
            mod_obj = bulk_data.get(ext_id, {})
            summary = mod_obj.get('summary')
            logo    = mod_obj.get('logo', {}).get('url') if mod_obj.get('logo') else None
            shots   = mod_obj.get('screenshots', [])

            # Insert screenshots
            cursor = conn.cursor()
            for order, shot in enumerate(shots):
                shot_url = shot.get('url')
                if shot_url:
                    cursor.execute(
                        'INSERT OR IGNORE INTO mod_screenshots (mod_id, screenshot_url, display_order) VALUES (?, ?, ?)',
                        (mod_id, shot_url, order)
                    )

            # 3. Fetch full HTML description
            time.sleep(DELAY_S)
            desc_html = fetch_description(ext_id)

            # Update mod row
            cursor.execute('''
                UPDATE mods 
                SET summary = ?, description = ?, logo_url = ?
                WHERE mod_id = ?
            ''', (summary, desc_html, logo, mod_id))
            
            conn.commit()
            print("✓")
            ok += 1
        except Exception as e:
            print(f"FAIL: {e}")
            fail += 1

    return ok, fail

def main():
    if not API_KEY:
        print("ERROR: CURSEFORGE_API_KEY not found in .env")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # We need to backfill any mod that is missing description OR logo_url
    rows = conn.execute("""
        SELECT mod_id, external_id, title
        FROM mods
        WHERE platform = 'curseforge'
          AND (description IS NULL OR logo_url IS NULL)
        ORDER BY mod_id
    """).fetchall()
    
    total = len(rows)
    if total == 0:
        print("All CurseForge mods are already fully backfilled!")
        sys.exit(0)

    print(f"Mods missing metadata: {total}")
    print(f"Estimated time: ~{total * DELAY_S // 60:.0f} minutes at {DELAY_S}s/call\n")

    chunk_size = 50
    chunks = [rows[i:i + chunk_size] for i in range(0, total, chunk_size)]

    total_ok, total_fail = 0, 0
    for chunk_idx, chunk in enumerate(chunks, 1):
        print(f"\n--- Chunk {chunk_idx}/{len(chunks)} ---")
        ok, fail = process_chunk(conn, chunk)
        total_ok += ok
        total_fail += fail

    conn.close()
    print(f"\n=== DONE: {total_ok} updated, {total_fail} failed ===")

if __name__ == '__main__':
    main()
