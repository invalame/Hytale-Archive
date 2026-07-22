import os
import time
import requests
import sqlite3
from dotenv import load_dotenv
from crawler_core import CrawlerCore, SafetyStopException
from db_manager import DBManager

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), 'archivo_hytale.db')

def repair_modifold():
    token = os.environ.get('MODIFOLD_API_KEY')
    headers = {
        'User-Agent': 'HytaleArchiveBot/1.0 (Contact: pemaidana0@gmail.com)',
        'Authorization': f"Bearer {token}" if token else "",
        'Accept': 'application/json'
    }
    db = DBManager()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("=== Repairing Modifold: authors + versions ===")
    updated_authors = 0
    inserted_versions = 0
    current_page = 1

    while True:
        print(f"Fetching page {current_page}...")
        time.sleep(1.0)
        resp = requests.get(f"https://api.modifold.com/projects?page={current_page}", headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"Error {resp.status_code}, stopping.")
            break
        data = resp.json()
        projects = data.get('projects', [])
        if not projects:
            break

        for p in projects:
            owner = p.get('owner', {})
            real_author = owner.get('username', 'Unknown') if owner else 'Unknown'
            external_id = str(p.get('id', ''))

            conn.execute(
                "UPDATE mods SET author = ? WHERE platform = 'modifold' AND external_id = ?",
                (real_author, external_id)
            )
            updated_authors += conn.total_changes

            row = conn.execute(
                "SELECT mod_id FROM mods WHERE platform = 'modifold' AND external_id = ?",
                (external_id,)
            ).fetchone()

            if row:
                mod_id = row['mod_id']
                version_number = p.get('updated_at', 'unknown')
                published_at = p.get('created_at', '')
                result = conn.execute(
                    "INSERT OR IGNORE INTO mod_versions (mod_id, version_number, published_at, file_path, image_path, sha256_hash, platform_hash) VALUES (?, ?, ?, NULL, NULL, NULL, NULL)",
                    (mod_id, version_number, published_at)
                )
                if result.rowcount > 0:
                    inserted_versions += 1

        conn.commit()
        total_pages = data.get('totalPages', 1)
        if current_page >= total_pages:
            break
        current_page += 1

    conn.close()
    print(f"Modifold repair done. Authors updated, versions inserted: {inserted_versions}")

def repair_curseforge():
    api_key = os.environ.get('CURSEFORGE_API_KEY')
    headers = {
        'User-Agent': 'HytaleArchiveBot/1.0 (Contact: pemaidana0@gmail.com)',
        'x-api-key': api_key if api_key else "",
        'Accept': 'application/json'
    }
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("\n=== Repairing CurseForge: versions ===")
    inserted_versions = 0
    page_size = 50
    current_index = 0
    page = 1

    while True:
        print(f"Fetching page {page} (index={current_index})...")
        time.sleep(2.0)
        resp = requests.get(
            f"https://api.curseforge.com/v1/mods/search?gameId=70216&pageSize={page_size}&index={current_index}",
            headers=headers, timeout=15
        )
        if resp.status_code != 200:
            print(f"Error {resp.status_code}, stopping.")
            break
        data = resp.json()
        mods = data.get('data', [])
        if not mods:
            break

        for mod in mods:
            external_id = str(mod.get('id', ''))
            row = conn.execute(
                "SELECT mod_id FROM mods WHERE platform = 'curseforge' AND external_id = ?",
                (external_id,)
            ).fetchone()

            if row:
                mod_id = row['mod_id']
                latest_files = mod.get('latestFiles', [])
                if latest_files:
                    f = latest_files[0]
                    file_name = f.get('fileName', 'unknown')
                    published_at = f.get('fileDate', '')
                    sha1_hash = None
                    for h in f.get('hashes', []):
                        if h.get('algo') == 1:
                            sha1_hash = h.get('value')
                            break
                    result = conn.execute(
                        "INSERT OR IGNORE INTO mod_versions (mod_id, version_number, published_at, file_path, image_path, sha256_hash, platform_hash) VALUES (?, ?, ?, NULL, NULL, NULL, ?)",
                        (mod_id, file_name, published_at, sha1_hash)
                    )
                    if result.rowcount > 0:
                        inserted_versions += 1

        conn.commit()
        current_index += page_size
        page += 1
        if len(mods) < page_size:
            break

    conn.close()
    print(f"CurseForge repair done. Versions inserted: {inserted_versions}")

def verify():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print("\n=== Verification ===")

    print("\n--- 3 sample Modifold mods (checking real authors) ---")
    for row in conn.execute("SELECT title, author FROM mods WHERE platform='modifold' LIMIT 3"):
        print(f"  '{row['title']}' by '{row['author']}'")

    print("\n--- 3 sample CurseForge mods (checking authors) ---")
    for row in conn.execute("SELECT title, author FROM mods WHERE platform='curseforge' LIMIT 3"):
        print(f"  '{row['title']}' by '{row['author']}'")

    print("\n--- 3 sample mod_versions (Modifold - sha256=NULL, platform_hash=NULL) ---")
    for row in conn.execute("""
        SELECT m.title, v.version_number, v.sha256_hash, v.platform_hash
        FROM mod_versions v JOIN mods m ON v.mod_id = m.mod_id
        WHERE m.platform = 'modifold' LIMIT 3
    """):
        print(f"  '{row['title']}' | ver: {row['version_number'][:30]} | sha256: {row['sha256_hash']} | platform_hash: {row['platform_hash']}")

    print("\n--- 3 sample mod_versions (CurseForge - sha256=NULL, platform_hash=SHA1) ---")
    for row in conn.execute("""
        SELECT m.title, v.version_number, v.sha256_hash, v.platform_hash
        FROM mod_versions v JOIN mods m ON v.mod_id = m.mod_id
        WHERE m.platform = 'curseforge' LIMIT 3
    """):
        print(f"  '{row['title']}' | sha256: {row['sha256_hash']} | SHA1: {row['platform_hash']}")

    print("\n--- 2 sample blog_posts (checking real content + hash) ---")
    for row in conn.execute("SELECT title, html_sha256_hash, length(html_content) as html_len FROM blog_posts LIMIT 2"):
        print(f"  '{row['title']}' | sha256: {row['html_sha256_hash'][:20]}... | html_len: {row['html_len']} chars")

    print("\n--- Counts ---")
    for tbl in ['mods', 'mod_versions', 'blog_posts']:
        c = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {c}")

    conn.close()

if __name__ == '__main__':
    repair_modifold()
    repair_curseforge()
    verify()
