"""Playwright-based web page scraper with stealth anti-detection.

Scrapes a URL by launching a headless Chromium browser, extracts clean text,
and generates a PDF. Falls back to Google Cache if Playwright fails.
"""

import asyncio
import os
import random
import re
import tempfile
from pathlib import Path

import httpx

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Version/17.5 Safari/605.1.15",
]

VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
]

STEALTH_SCRIPT = """() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['es-ES','es','en'] });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    window.chrome = { runtime: {} };
    const q = navigator.permissions.query;
    navigator.permissions.query = (p) =>
        p.name==='notifications' ? Promise.resolve({state:'denied'}) : q(p);
}"""

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

_PLAYWRIGHT_AVAILABLE = None


def _check_playwright():
    global _PLAYWRIGHT_AVAILABLE
    if _PLAYWRIGHT_AVAILABLE is None:
        try:
            import playwright  # noqa: F401
            _PLAYWRIGHT_AVAILABLE = True
        except ImportError:
            _PLAYWRIGHT_AVAILABLE = False
    return _PLAYWRIGHT_AVAILABLE


_PLAYWRIGHT_WARNED = False


def _warn_playwright_missing():
    global _PLAYWRIGHT_WARNED
    if not _PLAYWRIGHT_WARNED:
        print("[!] Playwright not found. URLs will be added directly.")
        print("    Install for automatic scraping: pip install 'unb-consultant[scraping]'")
        print("    Then run: playwright install chromium")
        _PLAYWRIGHT_WARNED = True


async def _scrape_page_playwright(url: str, timeout_ms: int = 60000) -> tuple:
    """Scrape a URL using stealth Playwright.

    Returns (text_content, pdf_path_or_None).
    """
    from playwright.async_api import async_playwright

    text_content = None
    pdf_path = None

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport=random.choice(VIEWPORTS),
                locale="es-ES",
                timezone_id="America/Santiago",
                extra_http_headers=dict(HEADERS),
                bypass_csp=True,
            )
            page = await context.new_page()
            await page.add_init_script(STEALTH_SCRIPT)

            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

            await asyncio.sleep(1 + random.random() * 2)

            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await page.evaluate("window.scrollTo({ top: 300, behavior: 'instant' })")
            await asyncio.sleep(0.3)
            await page.evaluate("window.scrollTo({ top: 0, behavior: 'instant' })")

            text_content = await page.evaluate("""() => {
                const main = document.querySelector('article') || document.querySelector('main');
                if (main) return main.innerText;
                const c = document.body.cloneNode(true);
                for (const s of ['script','style','nav','footer','header','aside','noscript','iframe']) {
                    c.querySelectorAll(s).forEach(e => e.remove());
                }
                return c.innerText || '';
            }""")

            if not text_content or len(text_content.strip()) < 50:
                await asyncio.sleep(3)
                text_content = await page.evaluate("document.body.innerText || ''")

            if text_content and len(text_content.strip()) >= 50:
                tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                await page.pdf(path=str(tmp_pdf), format="A4", print_background=True)
                pdf_path = str(tmp_pdf)
        finally:
            await browser.close()

    return text_content, pdf_path


async def _try_google_cache(url: str) -> str | None:
    """Fallback: fetch text from Google Cache."""
    cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
    try:
        resp = httpx.get(cache_url, timeout=15, follow_redirects=True)
        if resp.status_code == 200:
            m = re.search(r'<pre[^>]*>(.*?)</pre>', resp.text, re.DOTALL)
            text = m.group(1) if m else re.sub(r'<[^>]+>', ' ', resp.text)
            return text.strip()
    except Exception:
        pass
    return None


def scrape_page_sync(url: str, timeout_ms: int = 60000) -> tuple:
    """Synchronous wrapper for scrape_page.

    Returns (text_content: str | None, pdf_path: str | None).

    If Playwright is not available or fails, falls back to Google Cache.
    If everything fails, returns (None, None).
    """
    if not _check_playwright():
        _warn_playwright_missing()
        return None, None

    try:
        text, pdf = asyncio.run(_scrape_page_playwright(url, timeout_ms))
    except Exception:
        text, pdf = None, None

    if text and len(text.strip()) >= 50:
        return text, pdf

    if pdf:
        try:
            os.remove(pdf)
        except Exception:
            pass

    cache_text = asyncio.run(_try_google_cache(url))
    if cache_text and len(cache_text.strip()) >= 50:
        return cache_text, None

    return None, None


def scrape_page_sync_with_fallback(url: str, timeout_ms: int = 60000) -> tuple:
    """Scrape a URL, with Google Cache fallback.

    Returns (text_content: str | None, pdf_path: str | None, used_fallback: bool).

    used_fallback is True when the URL was added directly (neither scrape nor
    cache succeeded).
    """
    text, pdf = scrape_page_sync(url, timeout_ms)
    if text:
        return text, pdf, False
    return None, None, True
