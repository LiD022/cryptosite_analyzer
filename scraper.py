"""
scraper.py — загрузка HTML со страниц сайтов.

Для каждого URL пытается получить:
  - homepage
  - /about, /terms, /legal (если доступен)
  - fallback на web.archive.org если сайт недоступен или заблокирован (403/429)
"""

import re
import httpx
from bs4 import BeautifulSoup

TIMEOUT = 15
# Реалистичные браузерные заголовки — обходят базовую анти-бот проверку
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}
EXTRA_PATHS = ["/about", "/terms", "/legal", "/privacy", "/faq"]

# Коды, при которых уходим в archive.org (заблокировано, недоступно)
_BLOCKED_CODES = {403, 429, 503, 520, 521, 522, 523, 524}


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
    lines = [l for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


def get_archive_url(url: str) -> str | None:
    """Ищет последний снапшот сайта на web.archive.org."""
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


def _try_archive_fallback(url: str, result: dict) -> None:
    """Заполняет result данными из web.archive.org."""
    archive_url = get_archive_url(url)
    if not archive_url:
        return
    result["archive_url"] = archive_url
    arch_html, arch_status = fetch_url(archive_url)
    if arch_html and arch_status and arch_status < 400:
        result["status"] = "inactive"
        result["pages_fetched"].append(archive_url)
        result["text"] += html_to_text(arch_html) + "\n\n"

        # Пробуем /terms из архива
        for path in ["/terms", "/terms-of-service", "/legal"]:
            terms_url = archive_url.rstrip("/") + path
            t_html, t_status = fetch_url(terms_url)
            if t_html and t_status and t_status < 400:
                result["pages_fetched"].append(terms_url)
                result["text"] += html_to_text(t_html) + "\n\n"
                break


def scrape_site(url: str) -> dict:
    """
    Главная функция. Возвращает dict:
    {
        "url": str,
        "status": "active" | "inactive" | "unreachable",
        "archive_url": str | None,
        "text": str,
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

    html, status_code = fetch_url(url)

    if html and status_code and status_code < 400:
        result["status"] = "active"
        result["pages_fetched"].append(url)
        result["text"] += html_to_text(html) + "\n\n"

        for path in EXTRA_PATHS:
            extra_html, extra_status = fetch_url(url + path)
            if extra_html and extra_status and extra_status < 400:
                result["pages_fetched"].append(url + path)
                result["text"] += html_to_text(extra_html) + "\n\n"

    elif status_code in _BLOCKED_CODES:
        # Сайт жив но блокирует — берём архив
        _try_archive_fallback(url, result)

    else:
        # Сайт недоступен (таймаут, DNS, SSL ошибка) — берём архив
        _try_archive_fallback(url, result)

    result["text"] = result["text"][:8000]
    return result


if __name__ == "__main__":
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
