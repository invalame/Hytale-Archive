import os
import time
import requests
from dotenv import load_dotenv
from crawler_core import CrawlerCore, SafetyStopException
from db_manager import DBManager

load_dotenv()

class CurseForgeScraper:
    def __init__(self):
        self.api_url = "https://api.curseforge.com/v1"
        self.api_key = os.environ.get('CURSEFORGE_API_KEY')
        self.core = CrawlerCore(target_url=self.api_url)
        self.db = DBManager()
        self.game_id = None

    def get_headers(self):
        return {
            'User-Agent': self.core.user_agent,
            'x-api-key': self.api_key if self.api_key else "",
            'Accept': 'application/json'
        }

    def fetch_api(self, endpoint):
        full_url = f"{self.api_url}{endpoint}"
        self.core.log_info(f"Fetching {full_url}...")
        time.sleep(2.0)

        response = requests.get(full_url, headers=self.get_headers(), timeout=15)
        self.core.check_safety_breaker(response.status_code, full_url, response.text)

        if response.status_code == 200:
            return response.json()
        else:
            self.core.log_error(f"CurseForge API Error {response.status_code} on {full_url}")
            return None

    def initialize_game_id(self):
        if self.game_id:
            return True
        self.core.log_info("Resolving Hytale gameId dynamically...")
        data = self.fetch_api("/games")
        if data and 'data' in data:
            for game in data['data']:
                if game.get('slug') == 'hytale':
                    self.game_id = game.get('id')
                    self.core.log_info(f"Hytale gameId found dynamically: {self.game_id}")
                    return True
        self.core.log_error("Could not resolve Hytale gameId.")
        return False

    def _extract_platform_hash(self, latest_files):
        if not latest_files:
            return None, None
        first_file = latest_files[0]
        file_name = first_file.get('fileName', 'unknown')
        published_at = first_file.get('fileDate', '')
        sha1_hash = None
        for h in first_file.get('hashes', []):
            if h.get('algo') == 1:
                sha1_hash = h.get('value')
                break
        return file_name, published_at, sha1_hash

    def run_scraper(self, max_pages=3):
        self.core.log_info(f"Starting CurseForge API Scraper (Max Pages: {max_pages})...")
        stats = {"extracted": 0, "new": 0, "duplicates": 0}

        if not self.api_key:
            self.core.log_error("CurseForge API Key missing in .env")
            return stats

        if not self.initialize_game_id():
            return stats

        page_size = 50
        current_index = 0
        pages_processed = 0

        while pages_processed < max_pages:
            search_data = self.fetch_api(f"/mods/search?gameId={self.game_id}&pageSize={page_size}&index={current_index}")
            if not search_data or 'data' not in search_data or len(search_data['data']) == 0:
                self.core.log_info("No more mods found on CurseForge.")
                break

            mods = search_data['data']
            self.core.log_info(f"Page {pages_processed + 1}: Found {len(mods)} mods.")

            for mod in mods:
                stats["extracted"] += 1
                authors = mod.get('authors', [])
                author_name = authors[0].get('name') if authors else "Unknown"

                mod_id, is_new = self.db.insert_or_ignore_mod(
                    platform="curseforge",
                    external_id=str(mod.get('id', 'unknown')),
                    title=mod.get('name', 'Unknown'),
                    author=author_name
                )

                if mod_id:
                    latest_files = mod.get('latestFiles', [])
                    result = self._extract_platform_hash(latest_files)
                    if result and len(result) == 3:
                        file_name, published_at, sha1_hash = result
                        dl_url = latest_files[0].get('downloadUrl') if latest_files else None
                        self.db.insert_or_ignore_version(
                            mod_id=mod_id,
                            version_number=file_name,
                            published_at=published_at,
                            file_path=None,
                            image_path=None,
                            sha256_hash=None,
                            platform_hash=sha1_hash,
                            download_url=dl_url
                        )

                    # Save enriched metadata: description_short, logo, screenshots
                    import json as _json
                    desc_short = mod.get('summary')
                    logo_url   = mod.get('logo', {}).get('url') if mod.get('logo') else None
                    self.db.update_mod_metadata(mod_id, description_short=desc_short, logo_url=logo_url)

                    # Insert each screenshot into mod_screenshots (idempotent via UNIQUE constraint)
                    for order, shot in enumerate(mod.get('screenshots', [])):
                        shot_url = shot.get('url')
                        if shot_url:
                            self.db.insert_or_ignore_screenshot(mod_id, shot_url, order)

                if is_new:
                    stats["new"] += 1
                else:
                    stats["duplicates"] += 1

            pages_processed += 1
            current_index += page_size

        self.core.log_info(f"CurseForge scraping complete. Stats: {stats}")
        return stats

if __name__ == '__main__':
    scraper = CurseForgeScraper()
    scraper.run_scraper(max_pages=3)
