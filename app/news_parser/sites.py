import httpx
import feedparser
from datetime import datetime

from bs4 import BeautifulSoup

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Удаляем все картинки
    for img in soup.find_all("img"):
        img.decompose()

    # Удаляем все ссылки целиком
    for a in soup.find_all("a"):
        a.decompose()
    return soup.get_text(strip=True)


def parse_rss(url: str):
     with httpx.Client(timeout=10, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        feed = feedparser.parse(r.text)


        posts = []
        for entry in feed.entries:
            published = None
            # преобразуем дату публикации в объект datetime
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])

            posts.append({
                "title": entry.title,
                "link": entry.link,
                "summary": html_to_text(entry.summary),
                "published_at": published
            })

        return posts


# выполняем smoke-тест для функции rss-парсинга
if __name__ == "__main__":
    url = "https://habr.com/ru/rss/"
    posts = parse_rss(url)

    for post in posts:
        print(f"{post['published_at']} | {post['title']}")
        print(post['link'])
        print(post['summary'])
        print("-" * 80)
