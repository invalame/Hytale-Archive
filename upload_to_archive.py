"""
upload_to_archive.py — Phase 6: Internet Archive integration
- Downloads files from original URLs into a temp dir
- Uploads all files for a Mod/Post to the SAME Internet Archive Item.
- EXTREMELY IMPORTANT: Uploads files ONE AT A TIME with a strict delay. 
  (IA does not support multi-file batch uploads at the HTTP level; the python library
   just fires them as fast as possible, which triggers the "appears to be spam" filter).
- Handles 503 Slow Down rate limiting with retries and Circuit Breaker.
"""
import os
import sys
import sqlite3
import time
import json
import tempfile
import requests
from bs4 import BeautifulSoup
from internetarchive import upload as ia_upload_raw
from dotenv import load_dotenv
from db_manager import DBManager

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), 'archivo_hytale.db')

IA_ACCESS_KEY = os.environ.get('IA_ACCESS_KEY')
IA_SECRET_KEY = os.environ.get('IA_SECRET_KEY')
USER_AGENT    = "HytaleArchiveBot/1.0 (Contact: pemaidana0@gmail.com)"

# ---------------------------------------------------------------------------
# Max number of items to upload per corrida.
# Mod batches: ~1.6 hours for 200 mods.
# Blog batches: ~1.3 hours for 30 blogs (assuming many images).
BATCH_SIZE_MODS = 200
BATCH_SIZE_BLOG = 30
# ---------------------------------------------------------------------------

# We MUST have a delay between individual files within the same Item
# otherwise the IA API triggers the "spam" 503 error for new accounts.
IA_DELAY_BETWEEN_FILES_S = 10    
IA_DELAY_BETWEEN_ITEMS_S = 10    
SLOW_DOWN_PAUSE_S        = 60   
MAX_503_RETRIES          = 3    
CIRCUIT_BREAKER_LIMIT    = 5    

CF_DELAY_S   = 2.0
BLOG_DELAY_S = 1.0


class SlowDownError(Exception):
    pass


def _download_to_temp(url, dest_path):
    headers = {'User-Agent': USER_AGENT}
    resp = requests.get(url, headers=headers, stream=True, timeout=30)
    resp.raise_for_status()
    with open(dest_path, 'wb') as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)


def _upload_single_file(identifier, file_name, file_path, metadata, is_first_file):
    """
    Upload exactly one file to an IA Item.
    Passing metadata on the first file creates/updates the Item.
    """
    for attempt in range(1, MAX_503_RETRIES + 1):
        try:
            meta_arg = metadata if is_first_file else {}
            responses = ia_upload_raw(
                identifier,
                files={file_name: file_path},
                metadata=meta_arg,
                access_key=IA_ACCESS_KEY,
                secret_key=IA_SECRET_KEY,
                retries=1,
                retries_sleep=0,
                checksum=True,
            )
            # Check for 503 in the actual HTTP response objects
            for r in (responses if isinstance(responses, list) else [responses]):
                if hasattr(r, 'status_code') and r.status_code == 503:
                    raise SlowDownError(f"503 Slow Down on {file_name}")
            return True

        except SlowDownError:
            if attempt < MAX_503_RETRIES:
                print(f"      ⚠ 503 Slow Down — pausing {SLOW_DOWN_PAUSE_S}s before retry {attempt + 1}/{MAX_503_RETRIES}...")
                time.sleep(SLOW_DOWN_PAUSE_S)
            else:
                raise
        except Exception as e:
            if '503' in str(e) and attempt < MAX_503_RETRIES:
                print(f"      ⚠ 503 Slow Down (Exception) — pausing {SLOW_DOWN_PAUSE_S}s before retry {attempt + 1}/{MAX_503_RETRIES}...")
                time.sleep(SLOW_DOWN_PAUSE_S)
                continue
            raise RuntimeError(f"Upload failed for {file_name}: {e}") from e


def _upload_files_to_item(identifier, files_dict, metadata):
    """
    Uploads all files to the SAME IA identifier, but ONE AT A TIME with a delay.
    This is critical because IA's API is 1 request per file, and batching them
    triggers the spam filter on new accounts.
    """
    uploaded  = 0
    failed    = []
    consecutive_503s = 0

    for i, (file_name, file_path) in enumerate(files_dict.items()):
        is_first = (i == 0)
        
        # Mandatory delay between files to avoid IA spam filter
        if i > 0:
            time.sleep(IA_DELAY_BETWEEN_FILES_S)

        print(f"    ^ [{i+1}/{len(files_dict)}] {file_name}...", end=' ', flush=True)

        try:
            _upload_single_file(identifier, file_name, file_path, metadata, is_first)
            print("OK")
            uploaded += 1
            consecutive_503s = 0

        except SlowDownError:
            print(f"FAIL (503 exhausted)")
            failed.append(file_name)
            consecutive_503s += 1
            if consecutive_503s >= CIRCUIT_BREAKER_LIMIT:
                print(f"\n  [CIRCUIT BREAKER] {consecutive_503s} consecutive 503s. Stopping upload.")
                raise
        except Exception as e:
            print(f"FAIL ({e})")
            failed.append(file_name)

    return uploaded, failed


def process_curseforge():
    print("\n=== CurseForge: Uploading Mods to Internet Archive ===")
    
    db   = DBManager()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT v.version_id, v.version_number, v.download_url, v.published_at,
               m.mod_id, m.external_id, m.title, m.author, m.summary, m.logo_url
        FROM mod_versions v
        JOIN mods m ON v.mod_id = m.mod_id
        WHERE m.platform    = 'curseforge'
          AND v.download_url IS NOT NULL
          AND (v.upload_status IS NULL OR v.upload_status != 'complete')
        ORDER BY v.version_id
    """).fetchall()

    total_pending   = len(rows)
    batch_limit     = BATCH_SIZE_MODS if BATCH_SIZE_MODS else total_pending
    rows_to_process = rows[:batch_limit]
    print(f"Total pending: {total_pending} | This batch: {len(rows_to_process)}\n")

    ok, fail = 0, 0

    for i, row in enumerate(rows_to_process, 1):
        version_id  = row['version_id']
        mod_id      = row['mod_id']
        external_id = row['external_id']
        version_num = row['version_number'] or 'unknown'
        dl_url      = row['download_url']
        title       = row['title']
        author      = row['author']
        date        = row['published_at']
        summary     = row['summary'] or ''
        logo_url    = row['logo_url']

        screenshots = conn.execute(
            "SELECT screenshot_url FROM mod_screenshots WHERE mod_id = ? ORDER BY display_order", 
            (mod_id,)
        ).fetchall()

        safe_ver   = "".join(c if c.isalnum() else '-' for c in version_num).strip('-').lower()[:40]
        identifier = f"hytale-archive-cf-{external_id}-{safe_ver}"

        metadata = {
            'title':       f"{title} ({version_num})",
            'mediatype':   'software',
            'creator':     author,
            'date':        date.split('T')[0] if date else '',
            'description': f"Archived Hytale mod from CurseForge.\nTitle: {title}\nAuthor: {author}\nVersion: {version_num}\n\n{summary}",
            'subject':     ['hytale', 'hytale-mod', 'curseforge'],
            'collection':  'opensource',
        }

        print(f"[{i}/{len(rows_to_process)}] {title} ({version_num})")
        print(f"  Identifier: {identifier}")

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                files_dict = {}
                
                temp_path = os.path.join(tmpdir, version_num)
                time.sleep(CF_DELAY_S)
                _download_to_temp(dl_url, temp_path)
                files_dict[version_num] = temp_path
                
                if logo_url:
                    logo_ext = os.path.splitext(logo_url.split('?')[0])[-1] or '.png'
                    logo_path = os.path.join(tmpdir, f"logo{logo_ext}")
                    time.sleep(CF_DELAY_S)
                    try:
                        _download_to_temp(logo_url, logo_path)
                        files_dict[f"logo{logo_ext}"] = logo_path
                    except Exception as e:
                        print(f"  Warning: could not download logo: {e}")
                        
                for idx, shot in enumerate(screenshots):
                    shot_url = shot['screenshot_url']
                    shot_ext = os.path.splitext(shot_url.split('?')[0])[-1] or '.png'
                    shot_name = f"screenshot_{idx+1}{shot_ext}"
                    shot_path = os.path.join(tmpdir, shot_name)
                    time.sleep(CF_DELAY_S)
                    try:
                        _download_to_temp(shot_url, shot_path)
                        files_dict[shot_name] = shot_path
                    except Exception as e:
                        print(f"  Warning: could not download screenshot {idx+1}: {e}")

                uploaded, failed_files = _upload_files_to_item(identifier, files_dict, metadata)
                
                if uploaded == 0:
                    raise ValueError("All file uploads failed")

            archive_url = f"https://archive.org/details/{identifier}"
            
            # Determine status based on failed files
            status = 'partial' if len(failed_files) > 0 else 'complete'
            db.update_version_archive_url(version_id, archive_url, status)
            
            if status == 'complete':
                print(f"  [OK] {archive_url}")
                ok += 1
            else:
                print(f"  [PARTIAL] {archive_url} (Missed {len(failed_files)} files)")
                # Partial counts as a failure for the summary, or we can count it as fail
                fail += 1

        except Exception as e:
            print(f"  [FAIL] {e}")
            fail += 1

        if i < len(rows_to_process):
            time.sleep(IA_DELAY_BETWEEN_ITEMS_S)

    conn.close()
    db.close()
    deferred = total_pending - len(rows_to_process)
    remaining_after = total_pending - len(rows_to_process) - fail
    print(f"\nCurseForge: {ok} uploaded, {fail} failed, {deferred} deferred to next run")
    return ok, fail


def process_blog_posts():
    print("\n=== Blog: Uploading Post Images to Internet Archive ===")
    
    db   = DBManager()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    posts = conn.execute("""
        SELECT post_id, url, title, published_at, html_content
        FROM blog_posts
        WHERE (upload_status IS NULL OR upload_status != 'complete')
    """).fetchall()
    conn.close()

    total_pending    = len(posts)
    batch_limit      = BATCH_SIZE_BLOG if BATCH_SIZE_BLOG else total_pending
    posts_to_process = posts[:batch_limit]
    print(f"Total pending: {total_pending} | This batch: {len(posts_to_process)}\n")

    ok, fail = 0, 0

    for i, post in enumerate(posts_to_process, 1):
        post_id = post['post_id']
        title   = post['title']
        date    = post['published_at']
        html    = post['html_content']
        slug    = post['url'].rstrip('/').split('/')[-1]

        identifier = f"hytale-archive-blog-{post_id}-{slug}"[:100]

        soup     = BeautifulSoup(html, 'html.parser')
        img_urls = []
        for img in soup.find_all('img'):
            url = img.get('data-src') or img.get('src')
            if url:
                if not url.startswith('http'):
                    url = "https://hytale.com" + url
                img_urls.append(url)

        print(f"[{i}/{len(posts_to_process)}] '{title}' — {len(img_urls)} images")
        print(f"  Identifier: {identifier}")

        if not img_urls:
            print("  No images found. Marking as done.")
            db.update_blog_archive_url(post_id, "NO_IMAGES")
            ok += 1
            continue

        metadata = {
            'title':       f"Hytale Blog: {title}",
            'mediatype':   'image',
            'creator':     'Hytale',
            'date':        date.split('T')[0] if date else '',
            'description': f"Archived images from the official Hytale blog post: {title}",
            'subject':     ['hytale', 'hytale-blog', 'official-art'],
            'collection':  'opensource',
        }

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                files_dict = {}
                for idx, img_url in enumerate(img_urls):
                    ext   = os.path.splitext(img_url.split('?')[0])[-1] or '.jpg'
                    fname = f"image_{idx:03d}{ext}"
                    dest  = os.path.join(tmpdir, fname)
                    try:
                        time.sleep(BLOG_DELAY_S)
                        _download_to_temp(img_url, dest)
                        files_dict[fname] = dest
                    except Exception as e:
                        print(f"  Warning: download failed {img_url[:60]}: {e}")

                if not files_dict:
                    raise ValueError("All image downloads failed — no files to upload")

                uploaded, failed_files = _upload_files_to_item(identifier, files_dict, metadata)

                if uploaded == 0:
                    raise ValueError("All file uploads failed")

            archive_url = f"https://archive.org/details/{identifier}"
            
            # Determine status
            status = 'partial' if len(failed_files) > 0 else 'complete'
            db.update_blog_archive_url(post_id, archive_url, status)
            
            if status == 'complete':
                print(f"  [OK] {archive_url}")
                ok += 1
            else:
                print(f"  [PARTIAL] {archive_url} (Missed {len(failed_files)} files)")
                fail += 1

        except Exception as e:
            print(f"  [FAIL] {e}")
            fail += 1

        if i < len(posts_to_process):
            time.sleep(IA_DELAY_BETWEEN_ITEMS_S)

    db.close()
    deferred = total_pending - len(posts_to_process)
    print(f"\nBlog: {ok} done, {fail} failed, {deferred} deferred to next run")
    return ok, fail


def main():
    if not IA_ACCESS_KEY or not IA_SECRET_KEY:
        print("ERROR: IA_ACCESS_KEY and IA_SECRET_KEY environment variables are required.")
        sys.exit(1)

    limit_msg = (f"BATCH MODE — {BATCH_SIZE_MODS} mods, {BATCH_SIZE_BLOG} blogs"
                 if (BATCH_SIZE_MODS or BATCH_SIZE_BLOG) else "FULL RUN — uploading everything")

    print("==========================================")
    print(f"Internet Archive Uploader — {limit_msg}")
    print(f"Rate limit: {IA_DELAY_BETWEEN_FILES_S}s/file | 503 pause: {SLOW_DOWN_PAUSE_S}s")
    print("==========================================")

    cf_ok, cf_fail     = process_curseforge()
    blog_ok, blog_fail = process_blog_posts()

    print("\n==========================================")
    print("               SUMMARY                   ")
    print("==========================================")
    print(f"  CurseForge:  {cf_ok} uploaded, {cf_fail} failed")
    print(f"  Blog images: {blog_ok} uploaded, {blog_fail} failed")
    if BATCH_SIZE_MODS or BATCH_SIZE_BLOG:
        print(f"\n  Batch mode active: Mods={BATCH_SIZE_MODS}, Blogs={BATCH_SIZE_BLOG}")
        print(f"  Run again to continue uploading the remaining items.")
    print("==========================================")


if __name__ == '__main__':
    main()
