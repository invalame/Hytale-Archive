import sqlite3

conn = sqlite3.connect('archivo_hytale.db')
try:
    conn.execute("ALTER TABLE mod_versions ADD COLUMN upload_status TEXT DEFAULT 'pending'")
except Exception:
    pass
try:
    conn.execute("ALTER TABLE blog_posts ADD COLUMN upload_status TEXT DEFAULT 'pending'")
except Exception:
    pass

# Repair targets
conn.execute("UPDATE mod_versions SET archive_url = NULL, upload_status = 'pending' WHERE mod_id = 807")
conn.execute("UPDATE blog_posts SET archive_url = NULL, upload_status = 'pending' WHERE post_id = 45")
# Set others
conn.execute("UPDATE mod_versions SET upload_status = 'complete' WHERE archive_url IS NOT NULL")
conn.execute("UPDATE blog_posts SET upload_status = 'complete' WHERE archive_url IS NOT NULL")

conn.commit()
conn.close()
print("Migration done")
