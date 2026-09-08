"""
Base module class + shared infrastructure for Nectar Marketplace scrapers.

Every marketplace module:
  * carries standardized metadata (id, name, category, price, version, ...)
  * can ``fetch`` a URL with browser-like, anti-bot mindful headers
  * implements :meth:`parse_html` so it is fully unit-testable offline
  * exposes a ``run(config)`` entry point that matches the WraithEngine task
    handler signature and returns a JSON ``TaskResult``
"""

from __future__ import annotations

import json
import random
import time
from typing import Any, Dict, List, Optional

from wraith.engine import TaskConfig, TaskResult

# A small pool of realistic desktop User-Agents so we can rotate per request.
# Rotating UA + full browser headers dramatically reduces the chance of a
# basic anti-bot / bot-detection wall refusing the request.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


class ScraperModule:
    """
    Base class for all Nectar Marketplace scraper modules.

    Subclasses MUST set :attr:`id`, :attr:`name`, :attr:`category` and
    implement :meth:`parse_html`. Metadata attributes fill the marketplace
    catalog and the ``MODULE_METADATA`` seed entries used by ``api/main.py``.
    """

    # ── Metadata (override in subclasses) ────────────────────────────────
    id: str = "base"
    name: str = "Base Module"
    category: str = "Scraping"
    price: int = 0
    price_label: str = "Free"
    version: str = "1.0.0"
    author: str = "Supra-Codex"
    description: str = ""
    features: List[str] = []
    requirements: List[str] = ["WraithEngine >= 0.1.0", "Python >= 3.9"]

    def metadata(self) -> Dict[str, Any]:
        """Return the marketplace catalog entry for this module."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "rating": 0.0,
            "downloads": 0,
            "price": self.price,
            "price_label": self.price_label,
            "category": self.category,
            "version": self.version,
            "install_count": 0,
            "features": self.features,
            "requirements": self.requirements,
        }

    # ── HTTP helpers ─────────────────────────────────────────────────────

    def headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build browser-like headers with a rotating User-Agent."""
        hdrs = dict(DEFAULT_HEADERS)
        hdrs["User-Agent"] = random.choice(USER_AGENTS)
        if extra:
            hdrs.update(extra)
        return hdrs

    def fetch(self, url: str, timeout: float = 30.0, extra_headers: Optional[Dict[str, str]] = None) -> str:
        """Fetch a URL and return its response body (HTML) as text."""
        import httpx

        resp = httpx.get(
            url,
            headers=self.headers(extra_headers),
            follow_redirects=True,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.text

    # ── To implement ─────────────────────────────────────────────────────

    def parse_html(self, html: str, url: str) -> Dict[str, Any]:
        """Parse raw HTML into a structured dict of extracted fields."""
        raise NotImplementedError

    # ── Task entry point (matches WraithEngine handler signature) ────────

    def run(self, config: TaskConfig) -> TaskResult:
        """Run the module against ``config.target`` (a URL)."""
        start = time.time()
        url = config.target
        try:
            html = self.fetch(url, timeout=config.timeout_seconds or 30)
            data = self.parse_html(html, url)
            data.setdefault("url", url)
            data.setdefault("status", "ok")
            return TaskResult(
                success=True,
                data=json.dumps(data, ensure_ascii=False, default=str),
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as exc:  # noqa: BLE001 - surface to caller
            return TaskResult(
                success=False,
                data=json.dumps({"url": url, "error": str(exc)}, ensure_ascii=False),
                error_message=str(exc),
                execution_time_ms=(time.time() - start) * 1000,
                exit_code=1,
            )


def _handler_for(module_class: type) -> Any:
    """Build a WraithEngine-compatible handler that runs a module instance."""
    def handler(config: TaskConfig) -> TaskResult:
        return module_class().run(config)
    return handler


# Registry of concrete module classes, populated by importing subclasses.
MODULE_CLASSES: Dict[str, type] = {}


def register_modules(engine) -> Dict[str, ScraperModule]:
    """
    Register every marketplace scraper module into a WraithEngine instance.

    Each module is installed under a task type equal to its ``id`` (e.g.
    ``mod-amazon-tracker``). Returns a mapping of ``id -> module instance``.
    """
    instances: Dict[str, ScraperModule] = {}
    for module_id, cls in MODULE_CLASSES.items():
        instance = cls()
        engine.register_module(module_id, _handler_for(cls))
        instances[module_id] = instance
    return instances


def _collect():
    """Auto-discover module classes that subclass ScraperModule."""
    for cls in ScraperModule.__subclasses__():
        if cls.id and cls.id != "base":
            MODULE_CLASSES[cls.id] = cls


_collect()
