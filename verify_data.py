import sqlite3
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), 'archivo_hytale.db')
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=== DATA VERIFICATION ===\n")

print("--- 5 Modifold mods (real authors, NOT placeholder) ---")
for row in conn.execute("SELECT title, author FROM mods WHERE platform='modifold' LIMIT 5"):
    print(f"  '{row['title']}' by '{row['author']}'")

print("\n--- 5 CurseForge mods ---")
for row in conn.execute("SELECT title, author FROM mods WHERE platform='curseforge' LIMIT 5"):
    print(f"  '{row['title']}' by '{row['author']}'")

print("\n--- 5 mod_versions Modifold (sha256=NULL, platform_hash=NULL expected) ---")
for row in conn.execute("""
    SELECT m.title, v.version_number, v.sha256_hash, v.platform_hash
    FROM mod_versions v JOIN mods m ON v.mod_id = m.mod_id
    WHERE m.platform = 'modifold' LIMIT 5
"""):
    print(f"  '{row['title']}' | ver: {row['version_number'][:30]} | sha256: {row['sha256_hash']} | platform_hash: {row['platform_hash']}")

print("\n--- 5 mod_versions CurseForge (sha256=NULL, platform_hash=SHA1 expected) ---")
for row in conn.execute("""
    SELECT m.title, v.version_number, v.sha256_hash, v.platform_hash
    FROM mod_versions v JOIN mods m ON v.mod_id = m.mod_id
    WHERE m.platform = 'curseforge' LIMIT 5
"""):
    print(f"  '{row['title'][:40]}' | sha256: {row['sha256_hash']} | SHA1: {row['platform_hash']}")

print("\n--- 3 blog_posts (real html_content length + real sha256) ---")
for row in conn.execute("""
    SELECT title, html_sha256_hash, length(html_content) as html_len
    FROM blog_posts LIMIT 3
"""):
    print(f"  '{row['title'][:55]}' | sha256: {row['html_sha256_hash'][:16]}... | html: {row['html_len']} chars")

print("\n--- COUNTS ---")
for tbl in ['mods', 'mod_versions', 'blog_posts']:
    c = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"  {tbl}: {c}")

print("\n--- mod_versions breakdown by platform ---")
for row in conn.execute("""
    SELECT m.platform, COUNT(*) as n
    FROM mod_versions v JOIN mods m ON v.mod_id = m.mod_id
    GROUP BY m.platform
"""):
    print(f"  {row['platform']}: {row['n']} versions")

print("\n--- Modifold mods still with placeholder author ---")
c = conn.execute("SELECT COUNT(*) FROM mods WHERE platform='modifold' AND author='NEEDS_REFRESH'").fetchone()[0]
print(f"  Remaining placeholder authors: {c}")

conn.close()
