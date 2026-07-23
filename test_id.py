import sqlite3
import re

conn = sqlite3.connect('archivo_hytale.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT m.external_id, v.version_number FROM mod_versions v JOIN mods m ON m.mod_id = v.mod_id WHERE m.external_id = '1431508'").fetchall()
for row in rows:
    version_num = row['version_number']
    safe_ver = ''.join(c if c.isalnum() else '-' for c in version_num).strip('-').lower()[:40]
    
    # We must ensure no double dashes or trailing dashes after truncation
    safe_ver_cleaned = re.sub(r'-+', '-', safe_ver).strip('-')

    identifier = f'hytale-archive-cf-{row["external_id"]}-{safe_ver}'
    identifier_cleaned = f'hytale-archive-cf-{row["external_id"]}-{safe_ver_cleaned}'
    
    print(f"Original: {repr(identifier)}")
    print(f"Cleaned:  {repr(identifier_cleaned)}")
    print(f"Matches Regex Original: {bool(re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{4,100}$', identifier))}")
    print(f"Matches Regex Cleaned:  {bool(re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{4,100}$', identifier_cleaned))}")

conn.close()
