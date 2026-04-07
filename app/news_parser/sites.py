# app/news_parser/sites.py

import httpx
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup
import re


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        img.decompose()
    for a in soup.find_all("a"):
        a.decompose()
    return soup.get_text(strip=True)


def extract_image_url(entry) -> str | None:
    """
    Извлекает URL изображения из RSS-элемента.
    Проверяет несколько возможных мест.
    """
    # 1. Media RSS: media:content или media:thumbnail
    media_content = entry.get("media_content")
    if media_content and isinstance(media_content, list):
        for media in media_content:
            if media.get("medium") == "image" or media.get("type", "").startswith("image/"):
                url = media.get("url")
                if url:
                    return url

    # 2. Media RSS: media:thumbnail
    media_thumbnail = entry.get("media_thumbnail")
    if media_thumbnail and isinstance(media_thumbnail, list) and media_thumbnail[0].get("url"):
        return media_thumbnail[0]["url"]

    # 3. Enclosure с типом image
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/") and enc.get("href"):
                return enc["href"]

    # 4. Элемент <image> в RSS 2.0
    if hasattr(entry, "image") and entry.image:
        img = entry.image
        if isinstance(img, dict) and img.get("href"):
            return img["href"]
        elif isinstance(img, str) and img.startswith("http"):
            return img

    # 5. Ищем <img> в description/content (HTML)
    for field in ["content", "description", "summary"]:
        if hasattr(entry, field):
            content = getattr(entry, field)
            # content может быть списком словарей с 'value'
            if isinstance(content, list):
                content = content[0].get("value", "") if content else ""
            if content and isinstance(content, str):
                soup = BeautifulSoup(content, "html.parser")
                img_tag = soup.find("img")
                if img_tag and img_tag.get("src"):
                    src = img_tag["src"]
                    # Преобразуем относительные URL в абсолютные, если есть link
                    if src and not src.startswith("http"):
                        if hasattr(entry, "link") and entry.link:
                            from urllib.parse import urljoin
                            src = urljoin(entry.link, src)
                    return src if src and src.startswith("http") else None

    return None


def parse_rss(url: str) -> list[dict]:
    with httpx.Client(timeout=10, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        feed = feedparser.parse(r.text)

        posts = []
        for entry in feed.entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])

            # 🔹 Извлекаем изображение
            image_url = extract_image_url(entry)

            posts.append({
                "title": entry.title,
                "link": entry.link,
                "summary": html_to_text(entry.summary) if hasattr(entry, "summary") else "",
                "published_at": published,
                "image": image_url,  # 🔹 Новое поле
            })

        return posts


# Smoke-тест
if __name__ == "__main__":
    url = "https://habr.com/ru/rss/"
    posts = parse_rss(url)
    for post in posts[:3]:
        print(f"🖼️ {post.get('image') or 'No image'}")
        print(f"📰 {post['title']}")
        print(f"🔗 {post['link']}")
        print("-" * 80)
