import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from crawler_core import CrawlerCore, SafetyStopException
from db_manager import DBManager

class HytaleBlogScraper:
    def __init__(self):
        self.base_url = "https://hytale.com"
        self.core = CrawlerCore(target_url=self.base_url)
        self.core.setup_robots(f"{self.base_url}/robots.txt")
        self.db = DBManager()

    def run_scraper(self, max_posts=10):
        self.core.log_info(f"Starting Hytale Blog Scraper (Max Posts: {max_posts})...")
        stats = {"extracted": 0, "new": 0, "duplicates": 0}
        news_url = "/news"

        if not self.core.can_fetch(news_url):
            self.core.log_error(f"robots.txt prevents fetching {news_url}")
            return stats

        full_url = f"{self.base_url}{news_url}"
        self.core.log_info(f"Fetching post list from {full_url}")
        headers = {'User-Agent': self.core.user_agent}

        try:
            response = requests.get(full_url, headers=headers, timeout=15)
            self.core.check_safety_breaker(response.status_code, full_url, response.text)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = []
                seen = set()
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/news/20' in href and href not in seen:
                        seen.add(href)
                        links.append(href)

                posts_to_process = links[:max_posts]
                self.core.log_info(f"Found {len(links)} real article URLs. Processing up to {max_posts}.")

                for post_path in posts_to_process:
                    stats["extracted"] += 1
                    is_new = self._process_post(post_path, headers)
                    if is_new:
                        stats["new"] += 1
                    else:
                        stats["duplicates"] += 1
            else:
                self.core.log_error(f"Failed to fetch news list. HTTP {response.status_code}")

        except SafetyStopException:
            raise
        except Exception as e:
            self.core.log_error(f"Exception during blog scraping: {e}")

        self.core.log_info(f"Hytale Blog scraping complete. Stats: {stats}")
        return stats

    def _process_post(self, post_path, headers):
        full_url = f"{self.base_url}{post_path}"
        time.sleep(2)

        try:
            response = requests.get(full_url, headers=headers, timeout=15)
            self.core.check_safety_breaker(response.status_code, full_url, response.text)

            if response.status_code != 200:
                self.core.log_error(f"HTTP {response.status_code} on {full_url}")
                return False

            soup = BeautifulSoup(response.text, 'html.parser')

            title_tag = soup.find('h1')
            title_text = title_tag.get_text(strip=True) if title_tag else ""
            if not title_text:
                self.core.log_error(f"Could not extract title for: {full_url}")
                return False

            published_at = ""
            time_tag = soup.find('time')
            if time_tag:
                published_at = time_tag.get('datetime', time_tag.get_text(strip=True))

            post_body = soup.find('div', class_='post-body')
            if not post_body:
                post_body = soup.find('main')
            if not post_body:
                self.core.log_error(f"Could not find post-body container for: {full_url}")
                post_body = soup

            html_content = str(post_body)
            html_sha256 = hashlib.sha256(html_content.encode('utf-8')).hexdigest()

            is_new = self.db.insert_or_ignore_blog(
                url=full_url,
                title=title_text,
                published_at=published_at,
                html_content=html_content,
                local_image_path=None,
                html_sha256_hash=html_sha256,
                image_sha256_hash=None
            )
            self.core.log_info(f"Post '{title_text[:60]}' — {'NEW' if is_new else 'DUPLICATE'}")
            return is_new

        except SafetyStopException:
            raise
        except Exception as e:
            self.core.log_error(f"Failed to process {full_url}: {e}")
            return False

if __name__ == '__main__':
    scraper = HytaleBlogScraper()
    scraper.run_scraper(max_posts=10)
