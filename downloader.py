import os
import sys
import time
import hashlib
import sqlite3
import shutil
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from db_manager import DBManager

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH  = os.path.join(os.path.dirname(__file__), 'archivo_hytale.db')
BASE_DIR = os.path.dirname(__file__)

DIRS = {
    "curseforge": os.path.join(BASE_DIR, "archivo_data", "mods", "curseforge"),
    "blog":       os.path.join(BASE_DIR, "archivo_data", "blog_images"),
}

MIN_FREE_SPACE_GB = 5
CF_DELAY_S        = 2.0
BLOG_DELAY_S      = 1.0

USER_AGENT = "HytaleArchiveBot/1.0 (Contact: pemaidana0@gmail.com)"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def ensure_dirs():
    for path in DIRS.values():
        os.makedirs(path, exist_ok=True)

def check_free_space():
    free_gb = shutil.disk_usage(BASE_DIR).free / (1024 ** 3)
    log(f"Free disk space: {free_gb:.1f} GB (minimum: {MIN_FREE_SPACE_GB} GB)")
    if free_gb < MIN_FREE_SPACE_GB:
        log("ABORT: Not enough disk space.")
        return False
    return True

def sha1_of_file(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def safe_filename(name):
    return "".join(c if c.isalnum() or c in '._- ' else '_' for c in name).strip()

def download_file(url, dest_path, headers=None):
    if headers is None:
        headers = {'User-Agent': USER_AGENT}
    resp = requests.get(url, headers=headers, stream=True, timeout=30)
    resp.raise_for_status()
    with open(dest_path, 'wb') as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)
    return True

def download_curseforge_zips():
    log("=== Phase 4: Downloading CurseForge .zip files ===")
    db   = DBManager()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT v.version_id, v.version_number, v.download_url, v.platform_hash,
               m.external_id, m.title
        FROM mod_versions v
        JOIN mods m ON v.mod_id = m.mod_id
        WHERE m.platform = 'curseforge'
          AND v.file_path IS NULL
          AND v.download_url IS NOT NULL
    """).fetchall()

    conn.close()

    total    = len(rows)
    success  = 0
    failed   = 0
    skipped  = 0
    fail_log = []

    log(f"Pending: {total} CurseForge .zip files")

    for i, row in enumerate(rows, 1):
        version_id   = row['version_id']
        version_num  = row['version_number']
        dl_url       = row['download_url']
        expected_sha1= row['platform_hash']
        title        = row['title']

        safe_name  = safe_filename(version_num or f"mod_{row['external_id']}")
        dest_path  = os.path.join(DIRS["curseforge"], safe_name)

        log(f"[{i}/{total}] {title[:50]} → {safe_name}")

        try:
            time.sleep(CF_DELAY_S)
            download_file(dl_url, dest_path)

            actual_sha1 = sha1_of_file(dest_path)

            if expected_sha1 and actual_sha1.lower() != expected_sha1.lower():
                os.remove(dest_path)
                raise ValueError(f"SHA1 mismatch! expected={expected_sha1} got={actual_sha1}")

            db.update_version_file_path(version_id, dest_path, actual_sha1)
            success += 1
            log(f"  OK — SHA1 verified: {actual_sha1[:16]}...")

        except Exception as e:
            failed += 1
            fail_log.append({"file": safe_name, "url": dl_url, "error": str(e)})
            log(f"  FAIL — {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)

    log(f"\nCurseForge downloads complete: {success} OK, {failed} FAILED, {skipped} skipped")
    return success, failed, fail_log

def download_blog_images():
    log("\n=== Phase 4: Downloading Blog post images ===")
    db   = DBManager()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    posts = conn.execute("""
        SELECT post_id, url, title, html_content
        FROM blog_posts
        WHERE local_image_path IS NULL
    """).fetchall()

    conn.close()

    total   = len(posts)
    success = 0
    failed  = 0
    fail_log= []

    log(f"Pending: {total} blog posts needing images")

    for i, post in enumerate(posts, 1):
        post_id  = post['post_id']
        title    = post['title']
        html     = post['html_content']

        log(f"[{i}/{total}] {title[:55]}")

        soup = BeautifulSoup(html, 'html.parser')
        imgs = soup.find_all('img', src=True)

        if not imgs:
            log(f"  No images found in post — skipping")
            skipped_img = True
            success += 1
            db.update_blog_image_path(post_id, "NO_IMAGES", None)
            continue

        post_dir  = os.path.join(DIRS["blog"], f"post_{post_id}")
        os.makedirs(post_dir, exist_ok=True)

        post_success = 0
        first_saved  = None
        first_hash   = None

        for img in imgs:
            src = img['src']
            if not src.startswith('http'):
                src = "https://hytale.com" + src

            ext       = os.path.splitext(src.split('?')[0])[-1] or '.img'
            fname     = safe_filename(os.path.basename(src.split('?')[0]))[:80] or f"img_{post_success}"
            dest_path = os.path.join(post_dir, fname)

            try:
                time.sleep(BLOG_DELAY_S)
                download_file(src, dest_path)
                img_hash = sha256_of_file(dest_path)

                if first_saved is None:
                    first_saved = dest_path
                    first_hash  = img_hash

                post_success += 1
                log(f"  IMG OK: {fname[:40]} sha256={img_hash[:12]}...")

            except Exception as e:
                failed += 1
                fail_log.append({"post": title, "url": src, "error": str(e)})
                log(f"  IMG FAIL: {src[:60]} — {e}")

        if first_saved:
            db.update_blog_image_path(post_id, first_saved, first_hash)
            success += 1
            log(f"  Post saved: {post_success} images → primary path activated")
        else:
            failed += 1

    log(f"\nBlog image downloads complete: {success} posts OK, {failed} posts FAILED")
    return success, failed, fail_log

def print_fail_log(label, fail_log):
    if fail_log:
        print(f"\n--- {label} failures ---")
        for entry in fail_log[:20]:
            print(f"  {entry}")
        if len(fail_log) > 20:
            print(f"  ... and {len(fail_log)-20} more. See log for full list.")

def main():
    print("==========================================")
    print(f"Hytale Archive Phase 4 Downloader")
    print(f"Started: {datetime.now()}")
    print("==========================================")

    ensure_dirs()

    if not check_free_space():
        return

    cf_ok, cf_fail, cf_fail_log    = download_curseforge_zips()
    blog_ok, blog_fail, blog_fails  = download_blog_images()

    total_size = 0
    for root, _, files in os.walk(os.path.join(BASE_DIR, "archivo_data")):
        for f in files:
            total_size += os.path.getsize(os.path.join(root, f))
    total_mb = total_size / (1024 ** 2)

    print("\n==========================================")
    print("         PHASE 4 DOWNLOAD SUMMARY         ")
    print("==========================================")
    print(f"  CurseForge .zip:  {cf_ok} downloaded, {cf_fail} failed")
    print(f"  Blog images:      {blog_ok} posts done, {blog_fail} failed")
    print(f"  Total disk used:  {total_mb:.1f} MB")
    print("==========================================")

    print_fail_log("CurseForge", cf_fail_log)
    print_fail_log("Blog images", blog_fails)

if __name__ == '__main__':
    main()
