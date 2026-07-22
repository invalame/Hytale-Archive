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

    def update_version_archive_url(self, version_id, archive_url):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE mod_versions SET archive_url = ? WHERE version_id = ?', (archive_url, version_id))
        self.conn.commit()

    def update_blog_archive_url(self, post_id, archive_url):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE blog_posts SET archive_url = ? WHERE post_id = ?', (archive_url, post_id))
        self.conn.commit()

    def close(self):
        self.conn.close()
