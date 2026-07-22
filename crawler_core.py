import time
import datetime
import urllib.robotparser
import os

class SafetyStopException(Exception):
    """Critical exception raised to halt crawling to prevent bans."""
    pass

class CrawlerCore:
    def __init__(self, target_url, user_agent="HytaleArchiveBot/1.0 (Contact: pemaidana0@gmail.com)"):
        self.target_url = target_url
        self.user_agent = user_agent
        self.log_file = os.path.join(os.path.dirname(__file__), 'scraper_logs.txt')
        self.rp = urllib.robotparser.RobotFileParser()
        
    def setup_robots(self, robots_url):
        """Fetches the real robots.txt for HTML scrapers"""
        try:
            self.rp.set_url(robots_url)
            self.rp.read()
        except Exception as e:
            self.log_error(f"Failed to load robots.txt from {robots_url}: {e}")

    def log_error(self, message):
        """Rule 4: Logs System"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_msg = f"[ERROR] {timestamp} - {message}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(error_msg)
        print(error_msg.strip())

    def log_info(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[INFO] {timestamp} - {message}")

    def can_fetch(self, url_path):
        """Rule 6: Respect robots.txt strictly"""
        full_url = f"{self.target_url}{url_path}"
        return self.rp.can_fetch(self.user_agent, full_url)

    def check_safety_breaker(self, status_code, url, response_text=""):
        """Triggers Circuit Breaker on 429 or 403."""
        if status_code in [403, 429]:
            msg = f"CRITICAL SAFETY STOP! HTTP {status_code} received on {url}."
            if response_text:
                msg += f"\nResponse Body: {response_text[:500]}"
            msg += "\nWaiting at least 1 hour is strongly recommended to avoid permanent IP ban."
            self.log_error(msg)
            raise SafetyStopException(msg)
