"""
scraper.py — загрузка HTML со страниц сайтов.

Для каждого URL пытается получить:
  - homepage
  - /about, /terms, /legal (если доступен)
  - fallback на web.archive.org если сайт недоступен
"""

import re
import httpx
from bs4 import BeautifulSoup

TIMEOUT = 10
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
EXTRA_PATHS = ["/about", "/terms", "/legal", "/privacy", "/faq"]


def fetch_url(url: str, timeout: int = TIMEOUT) -> tuple[str | None, int | None]:
    """Загружает URL, возвращает (html, status_code) или (None, None) при ошибке."""
    try:
        r = httpx.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)
        return r.text, r.status_code
    except Exception:
        return None, None


def html_to_text(html: str) -> str:
    """Извлекает чистый текст из HTML, убирает скрипты и стили."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Убираем пустые строки подряд
    lines = [l for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


def get_archive_url(url: str) -> str | None:
    """Ищет последний снапшот сайта на web.archive.org."""
    # archive.org API не принимает https:// префикс
    clean = re.sub(r"^https?://", "", url).rstrip("/")
    api = f"http://archive.org/wayback/available?url={clean}"
    try:
        r = httpx.get(api, timeout=TIMEOUT)
        data = r.json()
        snapshot = data.get("archived_snapshots", {}).get("closest", {})
        if snapshot.get("available"):
            return snapshot["url"]
    except Exception:
        pass
    return None


def scrape_site(url: str) -> dict:
    """
    Главная функция. Возвращает dict:
    {
        "url": str,
        "status": "active" | "unreachable",
        "archive_url": str | None,
        "text": str,        # весь собранный текст для анализа
        "pages_fetched": list[str],
    }
    """
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url

    result = {
        "url": url,
        "status": "unreachable",
        "archive_url": None,
        "text": "",
        "pages_fetched": [],
    }

    # 1. Главная страница
    html, status_code = fetch_url(url)
    if html and status_code and status_code < 400:
        result["status"] = "active"
        result["pages_fetched"].append(url)
        result["text"] += html_to_text(html) + "\n\n"

        # 2. Дополнительные страницы
        for path in EXTRA_PATHS:
            extra_html, extra_status = fetch_url(url + path)
            if extra_html and extra_status and extra_status < 400:
                result["pages_fetched"].append(url + path)
                result["text"] += html_to_text(extra_html) + "\n\n"
    else:
        # 3. Fallback: web.archive.org
        archive_url = get_archive_url(url)
        if archive_url:
            result["archive_url"] = archive_url
            arch_html, arch_status = fetch_url(archive_url)
            if arch_html:
                result["status"] = "inactive"
                result["pages_fetched"].append(archive_url)
                result["text"] += html_to_text(arch_html) + "\n\n"

    # Обрезаем текст до разумного размера (~8000 символов)
    result["text"] = result["text"][:8000]
    return result


if __name__ == "__main__":
    # Быстрый тест
    test_urls = [
        "https://roobet.com",
        "https://rollbit.com",
    ]
    for u in test_urls:
        r = scrape_site(u)
        print(f"\n{'='*60}")
        print(f"URL: {r['url']} | status: {r['status']}")
        print(f"Pages: {r['pages_fetched']}")
        print(f"Text preview: {r['text'][:300]}...")
