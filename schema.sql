-- schema.sql
-- Database structure for Hytale Archive

CREATE TABLE IF NOT EXISTS mods (
    mod_id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    summary TEXT,
    description TEXT,
    logo_url TEXT,
    screenshots_json TEXT,
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
    archive_url TEXT,
    upload_status TEXT DEFAULT 'pending',
    FOREIGN KEY(mod_id) REFERENCES mods(mod_id) ON DELETE CASCADE,
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
    image_sha256_hash TEXT,
    archive_url TEXT,
    upload_status TEXT DEFAULT 'pending',
    UNIQUE(url)
);

CREATE TABLE IF NOT EXISTS mod_screenshots (
    screenshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mod_id INTEGER NOT NULL,
    screenshot_url TEXT NOT NULL,
    display_order INTEGER NOT NULL,
    FOREIGN KEY(mod_id) REFERENCES mods(mod_id) ON DELETE CASCADE,
    UNIQUE(mod_id, screenshot_url)
);

CREATE TABLE IF NOT EXISTS reddit_posts (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subreddit TEXT NOT NULL,
    reddit_id TEXT NOT NULL UNIQUE,
    author TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    score INTEGER DEFAULT 0,
    published_at TEXT NOT NULL,
    content_html TEXT,
    media_url TEXT,
    media_local_path TEXT,
    archive_url TEXT,
    upload_status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS reddit_comments (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    reddit_id TEXT NOT NULL UNIQUE,
    parent_id TEXT,
    author TEXT NOT NULL,
    score INTEGER DEFAULT 0,
    published_at TEXT NOT NULL,
    content_html TEXT,
    is_new INTEGER DEFAULT 1,
    FOREIGN KEY(post_id) REFERENCES reddit_posts(post_id) ON DELETE CASCADE
);
