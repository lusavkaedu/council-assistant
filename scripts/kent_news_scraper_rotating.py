import requests
from bs4 import BeautifulSoup
import json
import time
import os

BASE_URL = "https://www.kentonline.co.uk"
SECTION_PATHS = [
    "/categories/politics/",
    "/categories/politics-podcasts/",
    "/categories/elections/",
    "/westminster-watch-kent/",
    "/westminster-watch-medway/"
]
HEADERS = {'User-Agent': 'Mozilla/5.0'}
SAVE_PATH = "/Users/lgfolder/github/council-assistant/data/news/kent_online/kent_politics_articles.json"

def fetch_all_article_links():
    all_links = set()
    for path in SECTION_PATHS:
        url = BASE_URL + path
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            for a in soup.select("a[href*='/kent/news/']"):
                href = a.get("href")
                if href and href.startswith("/kent/news/"):
                    all_links.add(BASE_URL + href)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
    return list(all_links)[:50]  # limit to 50 total links

def fetch_article_data(article_links):
    articles_data = []
    for url in article_links:
        time.sleep(1)
        try:
            article_res = requests.get(url, headers=HEADERS, timeout=10)
            article_soup = BeautifulSoup(article_res.text, 'html.parser')
            json_ld = article_soup.find("script", type="application/ld+json")
            if json_ld:
                try:
                    metadata = json.loads(json_ld.string)
                    title = metadata.get("headline")
                    date_published = metadata.get("datePublished")
                    author = metadata.get("author", {}).get("name")
                    tags = metadata.get("keywords", [])
                except Exception:
                    title, date_published, author, tags = None, None, None, []
            else:
                title, date_published, author, tags = None, None, None, []

            paragraphs = article_soup.select("div.PageContent p")
            article_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            article_data = {
                "title": title,
                "author": author,
                "date": date_published,
                "tags": tags,
                "url": url,
                "article_text": article_text
            }
            articles_data.append(article_data)
        except Exception as e:
            print(f"Error fetching article: {url} - {e}")
    return articles_data

def append_new_articles(articles_data):
    if os.path.exists(SAVE_PATH):
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            existing_articles = json.load(f)
    else:
        existing_articles = []

    existing_urls = {article["url"] for article in existing_articles}
    new_articles = [article for article in articles_data if article["url"] not in existing_urls]

    if new_articles:
        all_articles = existing_articles + new_articles
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        print(f"Added {len(new_articles)} new articles.")
    else:
        print("No new articles found.")

def main():
    article_links = fetch_all_article_links()
    print(f"Found {len(article_links)} article links.")
    articles_data = fetch_article_data(article_links)
    append_new_articles(articles_data)

if __name__ == "__main__":
    main()
