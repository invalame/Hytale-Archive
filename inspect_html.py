import requests
from bs4 import BeautifulSoup
import sys
sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'HytaleArchiveBot/1.0 (Contact: pemaidana0@gmail.com)'}
url = 'https://hytale.com/news/2026/7/first-look-chapter-1-and-more'
soup = BeautifulSoup(requests.get(url, headers=headers).text, 'html.parser')

candidates = ['article', 'main', 'section']
for tag in candidates:
    el = soup.select_one(tag)
    if el:
        print(f"[{tag}] FOUND | classes={el.get('class', [])} | {len(str(el))} chars")
    else:
        print(f"[{tag}] not found")

print()
print("All divs with an id attribute:")
for d in soup.find_all('div', id=True):
    print(f"  <div id='{d['id']}'> ({len(str(d))} chars)")

print()
print("All divs with class containing 'post', 'article', 'content', 'body':")
keywords = ['post', 'article', 'content', 'body', 'entry', 'prose']
for d in soup.find_all('div'):
    classes = ' '.join(d.get('class', []))
    if any(k in classes.lower() for k in keywords):
        print(f"  class='{classes}' | {len(str(d))} chars")
