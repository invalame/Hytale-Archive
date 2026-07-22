import sqlite3, shutil, os, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('archivo_hytale.db')
c = conn.cursor()

c.execute("""SELECT COUNT(*) FROM mod_versions v JOIN mods m ON v.mod_id=m.mod_id
             WHERE m.platform='curseforge' AND v.file_path IS NULL AND v.download_url IS NOT NULL""")
cf_zips = c.fetchone()[0]

c.execute("""SELECT COUNT(*) FROM mod_versions v JOIN mods m ON v.mod_id=m.mod_id
             WHERE m.platform='curseforge' AND v.download_url IS NULL""")
cf_no_url = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM blog_posts WHERE local_image_path IS NULL")
blog_pending = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM blog_posts")
blog_total = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM mods WHERE platform='curseforge'")
cf_mods = c.fetchone()[0]

conn.close()

free_gb = shutil.disk_usage(os.getcwd()).free / (1024**3)
space_ok = free_gb >= 5

print("=== ESTIMATION REPORT ===")
print(f"CurseForge mods in DB:         {cf_mods}")
print(f"CurseForge .zip to download:   {cf_zips}")
print(f"CurseForge entries w/o URL:    {cf_no_url}")
print(f"Blog posts total:              {blog_total}")
print(f"Blog posts pending images:     {blog_pending}")
print()
print(f"Free disk space:               {free_gb:.1f} GB")
print(f"MIN_FREE_SPACE_GB:             5 GB")
print(f"Space check:                   {'PASS' if space_ok else 'FAIL - ABORT'}")
print()
cf_minutes = (cf_zips * 2) // 60
print(f"Time estimate CurseForge:      {cf_zips} files x ~2s = ~{cf_minutes} min")
print(f"Time estimate Blog images:     fast (no rate-limit delay needed)")
