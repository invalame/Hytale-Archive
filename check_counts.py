import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('archivo_hytale.db')
cf = conn.execute("""
    SELECT COUNT(*) FROM mod_versions v
    JOIN mods m ON v.mod_id = m.mod_id
    WHERE m.platform = 'curseforge'
      AND v.download_url IS NOT NULL
      AND (v.upload_status IS NULL OR v.upload_status != 'complete')
""").fetchone()[0]
blog = conn.execute("""SELECT COUNT(*) FROM blog_posts
    WHERE (upload_status IS NULL OR upload_status != 'complete')""").fetchone()[0]
print(f"CF pending: {cf}  |  Blog pending: {blog}")
mins = (200 * 3 * 10) / 60
print(f"Estimated time for 200-mod batch: ~{mins:.0f} min (within 6h limit)")
conn.close()
