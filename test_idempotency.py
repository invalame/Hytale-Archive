import os
from db_manager import DBManager

def reset_db():
    db_path = os.path.join(os.path.dirname(__file__), 'archivo_hytale.db')
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Old database deleted.")

def run_test():
    reset_db() # Start clean
    print("Starting Strict Idempotency test...")
    db = DBManager()
    
    # Mock data for Mods
    platform = "curseforge"
    external_id = "999"
    title = "Test Mod"
    author = "Tester"
    version_number = "1.0"
    
    print("\n1. Inserting Mod 5 times in a loop...")
    for _ in range(5):
        db.insert_or_ignore_mod(platform, external_id, title, author)
        
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM mods")
    mods_count = cursor.fetchone()['count']
    print(f"Real DB Result - Saved Mods: {mods_count}")
    
    mod_id = db.insert_or_ignore_mod(platform, external_id, title, author)
    
    print("\n2. Inserting Mod Version 5 times in a loop...")
    for _ in range(5):
        db.insert_or_ignore_version(mod_id, version_number, "2026-07-21", "path.zip", "path.png", "hash123")
        
    cursor.execute("SELECT COUNT(*) as count FROM mod_versions")
    versions_count = cursor.fetchone()['count']
    print(f"Real DB Result - Saved Versions: {versions_count}")
    
    # Mock data for Blogs
    url_blog = "https://hytale.com/news/2026/07/test-post"
    title_blog = "Test Post"
    
    print("\n3. Inserting Blog Post 5 times in a loop...")
    for _ in range(5):
        db.insert_or_ignore_blog(url_blog, title_blog, "2026-07-21", "<p>HTML</p>", "/img/local.jpg", "hashHTML", "hashIMG")
        
    cursor.execute("SELECT COUNT(*) as count FROM blog_posts")
    blogs_count = cursor.fetchone()['count']
    print(f"Real DB Result - Saved Blogs: {blogs_count}")
    
    db.close()
    
    if mods_count == 1 and versions_count == 1 and blogs_count == 1:
        print("\n[SUCCESS] Idempotency via UNIQUE constraints works perfectly (COUNT = 1).")
    else:
        print("\n[FAILED] Duplicates were found in the database.")

if __name__ == '__main__':
    run_test()
