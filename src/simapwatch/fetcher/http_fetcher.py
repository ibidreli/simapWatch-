"""HTTP fetcher for loading SIMAP HTML pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.request import Request, urlopen


class HtmlFetcher(Protocol):
    """Abstraction for fetching HTML content."""

    def fetch_text(self, url: str) -> str:
        """Fetch URL and return decoded text."""


@dataclass
class HttpHtmlFetcher:
    """Simple urllib-based HTML fetcher."""

    timeout_seconds: int = 20
    user_agent: str = "simapWatch/0.1 (+https://www.simap.ch)"

    def fetch_text(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": self.user_agent})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

