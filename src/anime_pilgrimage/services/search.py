"""Web search and concurrent article extraction service."""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup
from ddgs import DDGS
from pydantic import BaseModel

from anime_pilgrimage.config import Settings, get_settings

logger = logging.getLogger(__name__)

_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_BLOCKED_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "pinterest.com",
    "amazon.com",
    "amazon.co.jp",
}


class SearchResult(BaseModel):
    """A single web search hit."""

    title: str
    url: str
    snippet: str = ""


class WebPage(BaseModel):
    """Fetched and cleaned readable page content."""

    url: str
    title: str = ""
    text: str
    status_code: int = 200


_HEADER_CHARSET_RE = re.compile(r"charset\s*=\s*['\"]?([a-zA-Z0-9._-]+)", re.IGNORECASE)


def _extract_header_charset(content_type: str) -> str | None:
    match = _HEADER_CHARSET_RE.search(content_type)
    return match.group(1).strip() if match else None


def extract_readable_text(
    html: str | bytes,
    *,
    max_chars: int = 6000,
    header_encoding: str | None = None,
) -> tuple[str, str]:
    """Extract page title and clean readable article text from HTML bytes or str.

    Accepts raw `bytes` plus optional HTTP `header_encoding` so both header-specified
    charsets and `<meta charset="Shift_JIS">` / EUC-JP pages decode deterministically.
    """
    title = ""
    if isinstance(html, bytes):
        soup = BeautifulSoup(html, "html.parser", from_encoding=header_encoding)
    else:
        soup = BeautifulSoup(html, "html.parser")

    if soup.title and soup.title.string:
        title = " ".join(soup.title.string.split()).strip()

    decoded_html: str | bytes = html
    if isinstance(html, bytes):
        resolved_encoding = header_encoding or getattr(soup, "original_encoding", None)
        if resolved_encoding:
            try:
                decoded_html = html.decode(resolved_encoding, errors="replace")
            except LookupError:
                decoded_html = html

    extracted = trafilatura.extract(
        decoded_html,
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )
    if not extracted:
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        extracted = "\n".join(
            line.strip() for line in soup.get_text("\n").splitlines() if line.strip()
        )

    cleaned = extracted.strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "..."
    return title, cleaned


class WebSearchService:
    """Searches the web (Tavily or free DuckDuckGo) and fetches readable pages concurrently."""

    TAVILY_URL = "https://api.tavily.com/search"

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http_client = http_client
        self._owns_client = http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self.settings.crawler_request_timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": _BROWSER_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
                },
            )
        return self._http_client

    @staticmethod
    def _is_usable_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        host = parsed.netloc.lower().removeprefix("www.")
        if any(host == d or host.endswith(f".{d}") for d in _BLOCKED_DOMAINS):
            return False
        return not parsed.path.lower().endswith(
            (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".mp4")
        )

    async def _search_tavily(self, query: str, max_results: int) -> list[SearchResult]:
        client = await self._get_client()
        response = await client.post(
            self.TAVILY_URL,
            json={
                "api_key": self.settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
        )
        if response.status_code != 200:
            logger.warning("Tavily search failed (HTTP %d) for %r", response.status_code, query)
            return []
        results: list[SearchResult] = []
        for item in response.json().get("results") or []:
            url = item.get("url", "")
            if self._is_usable_url(url):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=url,
                        snippet=item.get("content", ""),
                    )
                )
        return results

    def _search_ddgs_sync(self, query: str, max_results: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        with DDGS() as ddgs:
            raw_items = ddgs.text(query, max_results=max_results) or []
        for item in raw_items:
            url = item.get("href") or item.get("url") or ""
            if self._is_usable_url(url):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=url,
                        snippet=item.get("body", "") or item.get("snippet", ""),
                    )
                )
        return results

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Execute a web search using Tavily (if configured) or free DDGS."""
        if self.settings.tavily_api_key.strip():
            try:
                hits = await self._search_tavily(query, max_results)
                if hits:
                    return hits
            except Exception as exc:
                logger.warning(
                    "Tavily search error for %r (%s: %r)", query, type(exc).__name__, exc
                )

        try:
            return await asyncio.to_thread(self._search_ddgs_sync, query, max_results)
        except Exception as exc:
            logger.warning(
                "DuckDuckGo search error for %r (%s: %r)", query, type(exc).__name__, exc
            )
            return []

    async def fetch_page(self, url: str, *, max_chars: int = 6000) -> WebPage | None:
        """Fetch a single URL and extract readable text from raw bytes."""
        if not self._is_usable_url(url):
            return None
        try:
            client = await self._get_client()
            response = await client.get(url)
            if response.status_code != 200:
                logger.debug("Skipping %s (HTTP %d)", url, response.status_code)
                return None
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None

            header_encoding = _extract_header_charset(response.headers.get("content-type", ""))
            # Pass raw bytes + explicit header charset so Shift_JIS / EUC-JP decode reliably
            title, text = extract_readable_text(
                response.content,
                max_chars=max_chars,
                header_encoding=header_encoding,
            )
            if len(text) < 80:
                return None
            return WebPage(
                url=str(response.url),
                title=title,
                text=text,
                status_code=response.status_code,
            )
        except Exception as exc:
            logger.warning("Failed to fetch %s (%s: %r)", url, type(exc).__name__, exc)
            return None

    async def fetch_pages(
        self, urls: list[str], *, max_chars: int = 6000
    ) -> list[WebPage]:
        """Fetch multiple URLs concurrently respecting configured concurrency limits."""
        semaphore = asyncio.Semaphore(self.settings.crawler_max_concurrency)

        async def _bounded_fetch(target_url: str) -> WebPage | None:
            async with semaphore:
                return await self.fetch_page(target_url, max_chars=max_chars)

        tasks = [_bounded_fetch(url) for url in urls]
        fetched = await asyncio.gather(*tasks, return_exceptions=False)
        return [page for page in fetched if page is not None]

    async def aclose(self) -> None:
        if self._http_client is not None and self._owns_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> WebSearchService:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()
