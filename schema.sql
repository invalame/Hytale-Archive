-- schema.sql
-- Database structure for Hytale Archive

CREATE TABLE IF NOT EXISTS mods (
    mod_id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    -- Rule 1 & Database level idempotency
    UNIQUE(platform, external_id)
);

CREATE TABLE IF NOT EXISTS mod_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mod_id INTEGER NOT NULL,
    version_number TEXT NOT NULL,
    published_at TEXT NOT NULL,
    file_path TEXT,
    image_path TEXT,
    sha256_hash TEXT,
    platform_hash TEXT,
    download_url TEXT,
    FOREIGN KEY(mod_id) REFERENCES mods(mod_id),
    UNIQUE(mod_id, version_number)
);

-- NEW TABLE FOR BLOGS

CREATE TABLE IF NOT EXISTS blog_posts (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    published_at TEXT NOT NULL,
    html_content TEXT NOT NULL,
    local_image_path TEXT,
    html_sha256_hash TEXT,
    image_sha256_hash TEXT
);
