"""Web tools: web_search and web_fetch."""

import asyncio
import html
import json
import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from readability import Document

try:
    from ddgs import DDGS

    _DDGS_AVAILABLE = True
except ImportError:
    _DDGS_AVAILABLE = False

from clawbot.agent.security import NetworkSecurityPolicy
from clawbot.agent.tools.base import Tool
from clawbot.core.config.schema import WebSearchConfig

# Shared constants
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36"
MAX_REDIRECTS = 5  # Limit redirects to prevent DoS attacks


def _strip_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _normalize(text: str) -> str:
    """Normalize whitespace."""
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _validate_url(url: str) -> tuple[bool, str]:
    """Validate URL: must be http(s) with valid domain."""
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False, f"Only http/https allowed, got '{p.scheme or 'none'}'"
        if not p.netloc:
            return False, "Missing domain"
        return True, ""
    except Exception as e:
        return False, str(e)


class WebSearchTool(Tool):
    """Search the web using DuckDuckGo (no key), Brave Search, or SerpAPI."""

    name = "web_search"
    description = "Search the web. Returns titles, URLs, and snippets."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "count": {
                "type": "integer",
                "description": "Results (1-10)",
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["query"],
    }

    _KEYED_PROVIDERS: dict[str, str] = {
        "brave": "BRAVE_API_KEY",
        "serpapi": "SERPAPI_API_KEY",
    }

    def __init__(self, config: WebSearchConfig) -> None:
        self._provider = config.provider
        self._max_results = config.max_results
        self._keys = {
            "brave": config.brave_api_key or os.environ.get("BRAVE_API_KEY", ""),
            "serpapi": config.serpapi_api_key or os.environ.get("SERPAPI_API_KEY", ""),
        }

    async def execute(self, query: str, count: int | None = None, **kwargs: Any) -> str:
        n = min(max(count or self._max_results, 1), 10)
        if self._provider == "duckduckgo":
            return await self._search_duckduckgo(query, n)
        key = self._keys.get(self._provider, "")
        if not key:
            env_var = self._KEYED_PROVIDERS.get(self._provider, "")
            return f"Error: {self._provider} API key not configured (set tools.web.search or {env_var})"
        if self._provider == "serpapi":
            return await self._search_serpapi(query, n)
        return await self._search_brave(query, n)

    async def _search_duckduckgo(self, query: str, n: int) -> str:
        if not _DDGS_AVAILABLE:
            return "Error: duckduckgo-search package not installed (pip install duckduckgo-search)"
        try:

            def _fetch() -> list[dict]:
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=n))

            results = await asyncio.to_thread(_fetch)
            if not results:
                return f"No results for: {query}"
            return self._format(query, results[:n], title="title", url="href", desc="body")
        except Exception as e:
            return f"Error: {e}"

    async def _search_brave(self, query: str, n: int) -> str:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": n},
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": self._keys["brave"],
                    },
                    timeout=10.0,
                )
                r.raise_for_status()
            results = r.json().get("web", {}).get("results", [])
            if not results:
                return f"No results for: {query}"
            return self._format(query, results[:n], title="title", url="url", desc="description")
        except Exception as e:
            return f"Error: {e}"

    async def _search_serpapi(self, query: str, n: int) -> str:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google",
                        "q": query,
                        "num": n,
                        "api_key": self._keys["serpapi"],
                    },
                    timeout=10.0,
                )
                r.raise_for_status()
            results = r.json().get("organic_results", [])
            if not results:
                return f"No results for: {query}"
            return self._format(query, results[:n], title="title", url="link", desc="snippet")
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def _format(query: str, results: list[dict], *, title: str, url: str, desc: str) -> str:
        lines = [f"Results for: {query}\n"]
        for i, item in enumerate(results, 1):
            lines.append(f"{i}. {item.get(title, '')}\n   {item.get(url, '')}")
            if snippet := item.get(desc):
                lines.append(f"   {snippet}")
        return "\n".join(lines)


class WebFetchTool(Tool):
    """Fetch and extract content from a URL using Readability."""

    name = "web_fetch"
    description = "Fetch URL and extract readable content (HTML → markdown/text)."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "extract_mode": {"type": "string", "enum": ["markdown", "text"], "default": "markdown"},
            "max_chars": {"type": "integer", "minimum": 100},
        },
        "required": ["url"],
    }

    def __init__(
        self,
        max_chars: int = 50000,
        ssrf_protection: bool = True,
        security_policy: NetworkSecurityPolicy | None = None,
    ):
        self.max_chars = max_chars
        self.ssrf_protection = ssrf_protection
        self._security_policy = security_policy or NetworkSecurityPolicy()

    async def execute(
        self, url: str, extract_mode: str = "markdown", max_chars: int | None = None, **kwargs: Any
    ) -> str:
        max_chars = max_chars or self.max_chars

        # Validate URL before fetching
        is_valid, error_msg = _validate_url(url)
        if not is_valid:
            return json.dumps({"error": f"URL validation failed: {error_msg}", "url": url})

        if self.ssrf_protection:
            ok, err = self._security_policy.validate_request_url(url)
            if not ok:
                return json.dumps({"error": err or "URL blocked by security policy", "url": url})

        try:
            async with httpx.AsyncClient(
                follow_redirects=True, max_redirects=MAX_REDIRECTS, timeout=30.0
            ) as client:
                r = await client.get(url, headers={"User-Agent": USER_AGENT})
                r.raise_for_status()

            ctype = r.headers.get("content-type", "")

            # JSON
            if "application/json" in ctype:
                text, extractor = json.dumps(r.json(), indent=2), "json"
            # HTML
            elif "text/html" in ctype or r.text[:256].lower().startswith(("<!doctype", "<html")):
                doc = Document(r.text)
                content = (
                    self._to_markdown(doc.summary())
                    if extract_mode == "markdown"
                    else _strip_tags(doc.summary())
                )
                text = f"# {doc.title()}\n\n{content}" if doc.title() else content
                extractor = "readability"
            else:
                text, extractor = r.text, "raw"

            truncated = len(text) > max_chars
            if truncated:
                text = text[:max_chars]

            return json.dumps(
                {
                    "url": url,
                    "final_url": str(r.url),
                    "status": r.status_code,
                    "extractor": extractor,
                    "truncated": truncated,
                    "length": len(text),
                    "text": text,
                }
            )
        except Exception as e:
            return json.dumps({"error": str(e), "url": url})

    def _to_markdown(self, html: str) -> str:
        """Convert HTML to markdown."""
        # Convert links, headings, lists before stripping tags
        text = re.sub(
            r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
            lambda m: f"[{_strip_tags(m[2])}]({m[1]})",
            html,
            flags=re.I,
        )
        text = re.sub(
            r"<h([1-6])[^>]*>([\s\S]*?)</h\1>",
            lambda m: f"\n{'#' * int(m[1])} {_strip_tags(m[2])}\n",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"<li[^>]*>([\s\S]*?)</li>", lambda m: f"\n- {_strip_tags(m[1])}", text, flags=re.I
        )
        text = re.sub(r"</(p|div|section|article)>", "\n\n", text, flags=re.I)
        text = re.sub(r"<(br|hr)\s*/?>", "\n", text, flags=re.I)
        return _normalize(_strip_tags(text))
