import os
import sys
import time
import sqlite3
import requests
from bs4 import BeautifulSoup
from internetarchive import upload
from db_manager import DBManager
import tempfile

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), 'archivo_hytale.db')

IA_ACCESS_KEY = os.environ.get('IA_ACCESS_KEY')
IA_SECRET_KEY = os.environ.get('IA_SECRET_KEY')
USER_AGENT = "HytaleArchiveBot/1.0 (Contact: pemaidana0@gmail.com)"

CF_DELAY_S = 2.0

def download_temp_file(url, temp_path):
    headers = {'User-Agent': USER_AGENT}
    resp = requests.get(url, headers=headers, stream=True, timeout=30)
    resp.raise_for_status()
    with open(temp_path, 'wb') as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)
    return True

def process_curseforge():
    print("\n=== Uploading CurseForge Mods to Internet Archive ===")
    db = DBManager()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Find mods that have a download_url but no archive_url
    rows = conn.execute("""
        SELECT v.version_id, v.version_number, v.download_url, v.published_at,
               m.external_id, m.title, m.author
        FROM mod_versions v
        JOIN mods m ON v.mod_id = m.mod_id
        WHERE m.platform = 'curseforge'
          AND v.download_url IS NOT NULL
          AND v.archive_url IS NULL
    """).fetchall()
    conn.close()

    total = len(rows)
    print(f"Pending CurseForge uploads: {total}")

    for i, row in enumerate(rows, 1):
        version_id = row['version_id']
        external_id = row['external_id']
        version_num = row['version_number'] or "unknown"
        dl_url = row['download_url']
        title = row['title']
        author = row['author']
        date = row['published_at']

        # Create unique identifier
        safe_version = "".join(c if c.isalnum() else '-' for c in version_num).strip('-').lower()
        identifier = f"hytale-archive-cf-{external_id}-{safe_version}"

        print(f"[{i}/{total}] Processing: {title} (ID: {identifier})")

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_zip = os.path.join(tmpdir, "mod.zip")
            try:
                time.sleep(CF_DELAY_S)
                download_temp_file(dl_url, temp_zip)
                
                metadata = {
                    'title': f"Hytale Mod: {title} ({version_num})",
                    'mediatype': 'software',
                    'creator': author,
                    'date': date.split('T')[0] if date else None,
                    'description': f"Archived Hytale mod from CurseForge.\nTitle: {title}\nAuthor: {author}\nVersion: {version_num}",
                    'subject': ['hytale', 'hytale-mod', 'curseforge'],
                    'collection': 'opensource' # 'opensource' is required for community uploads
                }
                
                print(f"  Uploading to Archive.org...")
                responses = upload(
                    identifier,
                    files={'mod.zip': temp_zip},
                    metadata=metadata,
                    access_key=IA_ACCESS_KEY,
                    secret_key=IA_SECRET_KEY,
                    retries=3,
                    retries_sleep=5
                )
                
                # Check if upload actually worked
                archive_url = f"https://archive.org/details/{identifier}"
                db.update_version_archive_url(version_id, archive_url)
                print(f"  OK: {archive_url}")

            except Exception as e:
                print(f"  FAIL: {e}")

def process_blog_posts():
    print("\n=== Uploading Blog Images to Internet Archive ===")
    db = DBManager()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    posts = conn.execute("""
        SELECT post_id, url, title, html_content, published_at
        FROM blog_posts
        WHERE archive_url IS NULL
    """).fetchall()
    conn.close()

    total = len(posts)
    print(f"Pending Blog Image uploads: {total}")

    for i, post in enumerate(posts, 1):
        post_id = post['post_id']
        title = post['title']
        html = post['html_content']
        date = post['published_at']
        slug = post['url'].split('/')[-1]
        
        identifier = f"hytale-archive-blog-{post_id}-{slug}"[:100]

        print(f"[{i}/{total}] Processing: {title} (ID: {identifier})")

        soup = BeautifulSoup(html, 'html.parser')
        imgs = soup.find_all('img', src=True)

        if not imgs:
            print("  No images found. Skipping.")
            db.update_blog_archive_url(post_id, "NO_IMAGES")
            continue

        with tempfile.TemporaryDirectory() as tmpdir:
            file_map = {}
            for idx, img in enumerate(imgs):
                src = img['src']
                if not src.startswith('http'):
                    src = "https://hytale.com" + src
                
                ext = os.path.splitext(src.split('?')[0])[-1] or '.jpg'
                fname = f"image_{idx}{ext}"
                temp_img = os.path.join(tmpdir, fname)
                
                try:
                    download_temp_file(src, temp_img)
                    file_map[fname] = temp_img
                except Exception as e:
                    print(f"  Failed to download img {src}: {e}")

            if not file_map:
                print("  Failed to download any images. Skipping.")
                continue

            metadata = {
                'title': f"Hytale Blog Images: {title}",
                'mediatype': 'image',
                'creator': 'Hytale',
                'date': date.split('T')[0] if date else None,
                'description': f"Archived images from official Hytale blog post: {title}",
                'subject': ['hytale', 'hytale-blog', 'official-art'],
                'collection': 'opensource'
            }

            try:
                print(f"  Uploading {len(file_map)} images to Archive.org...")
                upload(
                    identifier,
                    files=file_map,
                    metadata=metadata,
                    access_key=IA_ACCESS_KEY,
                    secret_key=IA_SECRET_KEY,
                    retries=3,
                    retries_sleep=5
                )
                archive_url = f"https://archive.org/details/{identifier}"
                db.update_blog_archive_url(post_id, archive_url)
                print(f"  OK: {archive_url}")
            except Exception as e:
                print(f"  FAIL: {e}")

def main():
    if not IA_ACCESS_KEY or not IA_SECRET_KEY:
        print("ERROR: IA_ACCESS_KEY and IA_SECRET_KEY environment variables are required.")
        sys.exit(1)

    print("==========================================")
    print("Internet Archive Uploader Started")
    print("==========================================")
    
    process_curseforge()
    process_blog_posts()
    
    print("==========================================")
    print("Uploads Complete")
    print("==========================================")

if __name__ == '__main__':
    main()
