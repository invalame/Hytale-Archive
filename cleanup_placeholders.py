import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('archivo_hytale.db')
conn.execute("DELETE FROM blog_posts")
conn.commit()
print("blog_posts cleared:", conn.execute("SELECT COUNT(*) FROM blog_posts").fetchone()[0])
conn.close()
