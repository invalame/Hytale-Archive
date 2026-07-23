import os
import time
import requests
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from crawler_core import CrawlerCore
from db_manager import DBManager

class RedditScraper:
    def __init__(self):
        # We use a custom user agent per Reddit's general API guidelines, even for JSON
        self.user_agent = "HytaleArchiveBot/1.0 (Contact: pemaidana0@gmail.com)"
        self.core = CrawlerCore(target_url="https://www.reddit.com")
        self.core.user_agent = self.user_agent
        self.db = DBManager()
        
        self.subreddits = ['HytaleInfo', 'Hytale']
        # Limit the depth of /new.json we crawl per run. Usually 2-3 pages is plenty for a 3-hour cron.
        self.max_pages = 2
        
    def get_headers(self):
        return {
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        }
        
    def fetch_json(self, url):
        self.core.log_info(f"Fetching {url}")
        time.sleep(2.0)  # Be polite, Reddit rate limits heavily if you abuse JSON without OAuth
        try:
            resp = requests.get(url, headers=self.get_headers(), timeout=15)
            # Circuit breaker
            self.core.check_safety_breaker(resp.status_code, url, resp.text)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                self.core.log_error(f"Reddit returned {resp.status_code} for {url}")
                return None
        except Exception as e:
            self.core.log_error(f"Failed to fetch {url}: {e}")
            return None

    def _extract_media(self, post_data):
        media_url = None
        
        # Check for direct video via v.redd.it
        if post_data.get('is_video') and 'media' in post_data and post_data['media'] and 'reddit_video' in post_data['media']:
            # For reddit video, the actual URL can be extracted by yt-dlp later, but we store the fallback_url or just the post URL
            media_url = post_data['media']['reddit_video'].get('fallback_url')
        elif post_data.get('url'):
            url = post_data['url']
            # Direct image links
            if url.endswith(('.jpg', '.png', '.gif', '.jpeg', '.mp4')):
                media_url = url
            elif 'gallery' in url or 'reddit.com/gallery' in url:
                # Galleries require more complex parsing, usually media_metadata holds them
                pass 
                
        return media_url

    def _process_comment_node(self, post_id, comment_data, parent_id=None):
        if comment_data.get('kind') != 't1':
            return
            
        data = comment_data.get('data', {})
        author = data.get('author', '[deleted]')
        if author == '[deleted]':
            return
            
        reddit_id = data.get('name') # e.g. t1_xxxx
        score = data.get('score', 0)
        created_utc = data.get('created_utc')
        
        if not created_utc:
            return
            
        published_at = datetime.fromtimestamp(created_utc, timezone.utc).isoformat()
        content_html = data.get('body_html', '')
        
        # Insert or update comment
        self.db.insert_or_update_reddit_comment(
            post_id=post_id,
            reddit_id=reddit_id,
            parent_id=parent_id,
            author=author,
            score=score,
            published_at=published_at,
            content_html=content_html
        )
        
        # Recursively process replies
        replies = data.get('replies')
        if replies and isinstance(replies, dict) and replies.get('kind') == 'Listing':
            for child in replies.get('data', {}).get('children', []):
                self._process_comment_node(post_id, child, parent_id=reddit_id)

    def scan_new_posts(self):
        """Phase 1: Scan /new.json for each subreddit to find new posts."""
        self.core.log_info("--- Phase 1: Scanning /new.json ---")
        
        for sub in self.subreddits:
            after = None
            for page in range(self.max_pages):
                url = f"https://www.reddit.com/r/{sub}/new.json?limit=100"
                if after:
                    url += f"&after={after}"
                    
                data = self.fetch_json(url)
                if not data or 'data' not in data or not data['data'].get('children'):
                    break
                    
                children = data['data']['children']
                for child in children:
                    if child.get('kind') != 't3':
                        continue
                        
                    post = child['data']
                    reddit_id = post.get('name') # t3_xxx
                    title = post.get('title', '')
                    author = post.get('author', '[deleted]')
                    score = post.get('score', 0)
                    permalink = post.get('permalink', '')
                    full_url = f"https://www.reddit.com{permalink}"
                    created_utc = post.get('created_utc')
                    
                    if not created_utc:
                        continue
                        
                    published_at = datetime.fromtimestamp(created_utc, timezone.utc).isoformat()
                    content_html = post.get('selftext_html') or ''
                    
                    media_url = self._extract_media(post)
                    
                    self.db.insert_or_update_reddit_post(
                        subreddit=sub,
                        reddit_id=reddit_id,
                        author=author,
                        title=title,
                        url=full_url,
                        score=score,
                        published_at=published_at,
                        content_html=content_html,
                        media_url=media_url
                    )
                    
                after = data['data'].get('after')
                if not after:
                    break

    def refresh_recent_posts(self, days=14):
        """Phase 2: Refresh posts from the last N days to capture new comments and updated scores."""
        self.core.log_info(f"--- Phase 2: Refreshing posts from last {days} days ---")
        
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Get posts from DB
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT post_id, reddit_id, url FROM reddit_posts 
            WHERE published_at >= ?
            ORDER BY published_at DESC
        ''', (cutoff_date,))
        recent_posts = cursor.fetchall()
        
        self.core.log_info(f"Found {len(recent_posts)} recent posts to refresh.")
        
        for p in recent_posts:
            post_id = p['post_id']
            url = p['url']
            
            # The JSON endpoint for a post is just its url + .json
            json_url = f"{url.rstrip('/')}.json"
            data = self.fetch_json(json_url)
            
            if not data or not isinstance(data, list) or len(data) < 2:
                continue
                
            # data[0] is the post itself
            post_listing = data[0].get('data', {}).get('children', [])
            if post_listing:
                post_data = post_listing[0].get('data', {})
                score = post_data.get('score', 0)
                content_html = post_data.get('selftext_html') or ''
                
                # Update score and content
                cursor.execute('''
                    UPDATE reddit_posts SET score = ?, content_html = ? WHERE post_id = ?
                ''', (score, content_html, post_id))
                self.db.conn.commit()
                
            # data[1] contains the comments
            comments_listing = data[1].get('data', {}).get('children', [])
            for comment_node in comments_listing:
                self._process_comment_node(post_id, comment_node, parent_id=None)

    def run(self):
        self.core.log_info("Starting Reddit Scraper...")
        self.scan_new_posts()
        self.refresh_recent_posts(days=14)
        self.core.log_info("Reddit Scraper complete.")

if __name__ == '__main__':
    scraper = RedditScraper()
    scraper.run()
