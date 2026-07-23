import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'archivo_hytale.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

class DBManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    def insert_or_ignore_mod(self, platform, external_id, title, author):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO mods (platform, external_id, title, author)
            VALUES (?, ?, ?, ?)
        ''', (platform, external_id, title, author))
        is_new = cursor.rowcount > 0
        self.conn.commit()

        cursor.execute('SELECT mod_id FROM mods WHERE platform = ? AND external_id = ?', (platform, external_id))
        row = cursor.fetchone()
        return row['mod_id'] if row else None, is_new

    def update_mod_metadata(self, mod_id, description_short=None, logo_url=None):
        """Update non-version metadata for a mod (description_short, logo_url)."""
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE mods SET summary=?, logo_url=? WHERE mod_id=?',
            (description_short, logo_url, mod_id)
        )
        self.conn.commit()

    def insert_or_ignore_screenshot(self, mod_id, screenshot_url, display_order):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO mod_screenshots (mod_id, screenshot_url, display_order) VALUES (?, ?, ?)',
            (mod_id, screenshot_url, display_order)
        )
        self.conn.commit()

    def insert_or_ignore_version(self, mod_id, version_number, published_at, file_path, image_path, sha256_hash, platform_hash=None, download_url=None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO mod_versions 
            (mod_id, version_number, published_at, file_path, image_path, sha256_hash, platform_hash, download_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (mod_id, version_number, published_at, file_path, image_path, sha256_hash, platform_hash, download_url))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_version_file_path(self, version_id, file_path, sha256_hash):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE mod_versions SET file_path = ?, sha256_hash = ? WHERE version_id = ?',
            (file_path, sha256_hash, version_id)
        )
        self.conn.commit()

    def update_blog_image_path(self, post_id, local_image_path, image_sha256_hash):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE blog_posts SET local_image_path = ?, image_sha256_hash = ? WHERE post_id = ?',
            (local_image_path, image_sha256_hash, post_id)
        )
        self.conn.commit()

    def insert_or_ignore_blog(self, url, title, published_at, html_content, local_image_path, html_sha256_hash, image_sha256_hash):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO blog_posts
            (url, title, published_at, html_content, local_image_path, html_sha256_hash, image_sha256_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (url, title, published_at, html_content, local_image_path, html_sha256_hash, image_sha256_hash))
        is_new = cursor.rowcount > 0
        self.conn.commit()
        return is_new

    def update_version_archive_url(self, version_id, archive_url, status='complete'):
        """Update the archive URL and status for a specific mod version."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE mod_versions
            SET archive_url = ?, upload_status = ?
            WHERE version_id = ?
        ''', (archive_url, status, version_id))
        self.conn.commit()
            
    def update_version_upload_status(self, version_id, status):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE mod_versions SET upload_status = ? WHERE version_id = ?', (status, version_id))
        self.conn.commit()

    def update_blog_archive_url(self, post_id, archive_url, status='complete'):
        """Update the archive URL and status for a blog post."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE blog_posts
            SET archive_url = ?, upload_status = ?
            WHERE post_id = ?
        ''', (archive_url, status, post_id))
        self.conn.commit()

    def update_blog_upload_status(self, post_id, status):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE blog_posts SET upload_status = ? WHERE post_id = ?', (status, post_id))
        self.conn.commit()

    # --- Reddit Methods ---
    
    def insert_or_update_reddit_post(self, subreddit, reddit_id, author, title, url, score, published_at, content_html, media_url, media_local_path=None):
        cursor = self.conn.cursor()
        # Try to insert
        cursor.execute('''
            INSERT OR IGNORE INTO reddit_posts (subreddit, reddit_id, author, title, url, score, published_at, content_html, media_url, media_local_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (subreddit, reddit_id, author, title, url, score, published_at, content_html, media_url, media_local_path))
        
        is_new = cursor.rowcount > 0
        
        # If not new, we update the score and content_html (since self-text can be edited)
        if not is_new:
            cursor.execute('''
                UPDATE reddit_posts SET score = ?, content_html = ?
                WHERE reddit_id = ?
            ''', (score, content_html, reddit_id))
            
        self.conn.commit()
        
        cursor.execute('SELECT post_id FROM reddit_posts WHERE reddit_id = ?', (reddit_id,))
        row = cursor.fetchone()
        return row['post_id'] if row else None, is_new

    def insert_or_update_reddit_comment(self, post_id, reddit_id, parent_id, author, score, published_at, content_html):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO reddit_comments (post_id, reddit_id, parent_id, author, score, published_at, content_html)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (post_id, reddit_id, parent_id, author, score, published_at, content_html))
        
        is_new = cursor.rowcount > 0
        
        if not is_new:
            cursor.execute('''
                UPDATE reddit_comments SET score = ?, content_html = ?, is_new = 0
                WHERE reddit_id = ?
            ''', (score, content_html, reddit_id))
            
        self.conn.commit()
        return is_new

    def close(self):
        self.conn.close()
