import datetime
import shutil
import os
from crawler_core import SafetyStopException
from scraper_hytale_blog import HytaleBlogScraper
from scraper_curseforge import CurseForgeScraper

# --- CONFIGURATION (Safety Limits) ---
MAX_POSTS_HYTALE    = 88
MAX_PAGES_CURSEFORGE = 20
MIN_FREE_SPACE_GB   = 5
# To add a new scraper later (e.g. Reddit), add its import above and a new
# entry to SCRAPERS below — no other changes needed.
# -------------------------------------

SCRAPERS = [
    {
        "name": "Hytale Blog",
        "factory": lambda: HytaleBlogScraper(),
        "kwargs": {"max_posts": MAX_POSTS_HYTALE},
    },
    {
        "name": "CurseForge",
        "factory": lambda: CurseForgeScraper(),
        "kwargs": {"max_pages": MAX_PAGES_CURSEFORGE},
    },
    # Reddit placeholder — uncomment when scraper_reddit.py is ready:
    # {
    #     "name": "Reddit",
    #     "factory": lambda: RedditScraper(),
    #     "kwargs": {"max_posts": 100},
    # },
]

def check_free_space():
    free_bytes = shutil.disk_usage(os.path.dirname(__file__)).free
    free_gb = free_bytes / (1024 ** 3)
    print(f"[DISK] Free space: {free_gb:.1f} GB (minimum required: {MIN_FREE_SPACE_GB} GB)")
    if free_gb < MIN_FREE_SPACE_GB:
        print(f"[ABORT] Not enough free disk space. Stopping before downloads.")
        return False
    return True

def run_scraper_safe(entry):
    name    = entry["name"]
    scraper = entry["factory"]()
    kwargs  = entry["kwargs"]
    print(f"\n>>> Starting {name}...")
    try:
        stats = scraper.run_scraper(**kwargs)
        return stats
    except SafetyStopException as e:
        print(f"[ERROR] {name} hit Circuit Breaker: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] {name} crashed: {e}")
        return None

def print_summary(name, stats):
    if stats:
        print(f"  [{name}] Extracted: {stats['extracted']} | New: {stats['new']} | Duplicates: {stats['duplicates']}")
    else:
        print(f"  [{name}] FAILED or ABORTED")

def main():
    print("==========================================")
    print(f"Hytale Archive Master Scraper")
    print(f"Started: {datetime.datetime.now()}")
    print("==========================================")

    results = {}
    for entry in SCRAPERS:
        results[entry["name"]] = run_scraper_safe(entry)

    print("\n==========================================")
    print("           FINAL RUN SUMMARY              ")
    print("==========================================")
    for name, stats in results.items():
        print_summary(name, stats)
    print("==========================================")

if __name__ == '__main__':
    main()
