"""
SEO Audit Scanner — ``mod-seo-scanner``

Crawls a website (or single page) and produces an SEO health report:

  * meta tags (title, description, keywords, canonical, robots, OpenGraph)
  * heading structure (h1→h6 counts)
  * visible word count
  * page-speed indicators: response time, page size, resource counts
    (scripts, stylesheets, images, links)
  * broken-link scan (same-origin links, status-checked with a configurable cap)

Free module — designed to be the entry point for the Nectar free tier.

Behavior is configurable via the task payload (JSON string):

    {
      "max_pages": 3,          # crawl depth (same domain); 1 = single page
      "check_broken_links": true,
      "max_link_checks": 30    # cap on how many links get status-checked
    }
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import ScraperModule

_EXCLUDE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".pdf", ".zip",
                ".css", ".js", ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".xml", ".ico")
_EXCLUDE_PATH = ("mailto:", "tel:", "javascript:", "#", "data:", "blob:")


class SeoAuditScanner(ScraperModule):
    """Crawl a domain and report SEO meta, headings, speed and broken links."""

    id = "mod-seo-scanner"
    name = "SEO Audit Scanner"
    category = "SEO"
    price = 0
    price_label = "Free"
    version = "1.0.0"
    author = "Supra-Codex"
    description = (
        "Free SEO audit: crawl a domain and surface meta tags, heading "
        "structure, word count, page-speed hints and broken links."
    )
    features = [
        "Meta & OpenGraph extraction",
        "Heading (h1-h6) structure",
        "Word count analysis",
        "Page speed indicators",
        "Broken link scanning",
        "Same-domain crawl",
    ]
    requirements = ["WraithEngine >= 0.1.0", "Python >= 3.9", "beautifulsoup4", "lxml"]

    # ── Task entry point (extends base to support crawls + link checks) ──

    def run(self, config):
        """Run a single-page audit, or a small crawl when payload says so."""
        start = time.time()
        url = config.target
        opts: Dict[str, Any] = {}
        if config.payload:
            try:
                opts = json.loads(config.payload)
            except json.JSONDecodeError:
                opts = {"error": "payload must be valid JSON"}

        try:
            # Multi-page crawl
            max_pages = int(opts.get("max_pages", 1))
            if max_pages > 1:
                data = self.crawl(url, max_pages=max_pages,
                                  check_broken_links=bool(opts.get("check_broken_links", False)),
                                  max_link_checks=int(opts.get("max_link_checks", 30)))
            else:
                data = self.audit_single(url, check_broken_links=bool(opts.get("check_broken_links", False)),
                                         max_link_checks=int(opts.get("max_link_checks", 30)))
            data["options"] = opts
            data["status"] = "ok"
            from wraith.engine import TaskResult
            return TaskResult(
                success=True,
                data=json.dumps(data, ensure_ascii=False, default=str),
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as exc:  # noqa: BLE001
            from wraith.engine import TaskResult
            return TaskResult(
                success=False,
                data=json.dumps({"url": url, "error": str(exc)}, ensure_ascii=False),
                error_message=str(exc),
                execution_time_ms=(time.time() - start) * 1000,
                exit_code=1,
            )

    # ── Public API ──────────────────────────────────────────────────────

    def audit_single(self, url: str, check_broken_links: bool = False,
                     max_link_checks: int = 30) -> Dict[str, Any]:
        """Audit one page: fetch + parse + optional broken-link check."""
        fetch_start = time.time()
        html, final_url, elapsed = self._fetch_with_meta(url)
        page = self.parse_html(html, final_url)
        page["response_time_ms"] = round(elapsed * 1000, 1)
        page["final_url"] = final_url

        report = {
            "url": url,
            "pages_audited": 1,
            "pages": [page],
            "summary": self._summarize([page]),
        }
        if check_broken_links:
            report["broken_links"] = self.check_broken_links(final_url, html, max_checks=max_link_checks)
        return report

    def crawl(self, url: str, max_pages: int = 5, check_broken_links: bool = False,
              max_link_checks: int = 30) -> Dict[str, Any]:
        """BFS crawl of same-domain pages starting at ``url``."""
        domain = urlparse(url).netloc
        pages: List[Dict[str, Any]] = []
        visited: set = set()
        queue = [url]
        broken: List[Dict[str, Any]] = []

        while queue and len(pages) < max_pages:
            current = queue.pop(0)
            if current in visited or urlparse(current).netloc != domain:
                continue
            visited.add(current)
            try:
                html, final_url, elapsed = self._fetch_with_meta(current)
            except Exception:  # noqa: BLE001
                continue
            page = self.parse_html(html, final_url)
            page["response_time_ms"] = round(elapsed * 1000, 1)
            page["final_url"] = final_url
            pages.append(page)

            if check_broken_links and len(broken) < max_link_checks:
                broken.extend(self.check_broken_links(final_url, html, max_checks=max_link_checks - len(broken)))

            # Enqueue same-domain internal links for further crawling.
            for link in page.get("internal_links", []):
                queue.append(link)
                # de-dupe safely
                queue = list(dict.fromkeys(queue))

        return {
            "url": url,
            "pages_audited": len(pages),
            "pages": pages,
            "broken_links": broken,
            "summary": self._summarize(pages),
        }

    # ── Link checking ───────────────────────────────────────────────────

    def check_broken_links(self, page_url: str, html: str, max_checks: int = 30) -> List[Dict[str, Any]]:
        """Status-check same-origin links; return the broken/failed ones."""
        import httpx

        soup = BeautifulSoup(html, "lxml")
        base = urlparse(page_url)
        candidates: List[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or any(href.startswith(p) for p in _EXCLUDE_PATH):
                continue
            abs_url = urljoin(page_url, href)
            if urlparse(abs_url).netloc != base.netloc:
                continue
            if abs_url not in candidates:
                candidates.append(abs_url)

        broken: List[Dict[str, Any]] = []
        headers = self.headers({"Accept": "*/*", "Range": "bytes=0-0"})
        for link in candidates[:max_checks]:
            try:
                resp = httpx.get(link, headers=headers, follow_redirects=True, timeout=12)
                if resp.status_code >= 400:
                    broken.append({"url": link, "status": resp.status_code})
            except Exception as exc:  # noqa: BLE001
                broken.append({"url": link, "status": 0, "error": str(exc)[:120]})
        return broken

    # ── Internal: fetch with timing ─────────────────────────────────────

    def _fetch_with_meta(self, url: str):
        """Fetch and return (html, final_url, elapsed_seconds)."""
        import httpx

        start = time.time()
        resp = httpx.get(url, headers=self.headers(), follow_redirects=True, timeout=30)
        elapsed = time.time() - start
        resp.raise_for_status()
        return resp.text, str(resp.url), elapsed

    # ── Parsing (pure, unit-testable) ───────────────────────────────────

    def parse_html(self, html: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")

        meta = self._meta_tags(soup)
        headings = self._headings(soup)
        word_count = self._word_count(soup)
        resources = self._resources(soup, url)

        internal, external = self._links(soup, url)

        return {
            "url": url,
            "title": self._title(soup),
            "meta": meta,
            "headings": headings,
            "heading_counts": {f"h{i}": headings.get(f"h{i}", 0) for i in range(1, 7)},
            "word_count": word_count,
            "resources": resources,
            "internal_links": internal,
            "external_links": external,
            "suggestions": self._suggestions(meta, headings),
        }

    # ── Extractors ──────────────────────────────────────────────────────

    @staticmethod
    def _title(soup: BeautifulSoup) -> str:
        t = soup.find("title")
        return t.get_text(strip=True) if t else ""

    @staticmethod
    def _meta_tags(soup: BeautifulSoup) -> Dict[str, str]:
        meta: Dict[str, str] = {}
        for tag in soup.find_all("meta"):
            key = tag.get("name") or tag.get("property") or tag.get("http-equiv")
            content = tag.get("content")
            if key and content:
                meta[key.lower()] = content.strip()
        return meta

    @staticmethod
    def _headings(soup: BeautifulSoup) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            counts[tag] = len(soup.find_all(tag))
        return counts

    @staticmethod
    def _word_count(soup: BeautifulSoup) -> int:
        # Remove script/style/noscript content, then count words in visible text.
        for node in soup.find_all(["script", "style", "noscript"]):
            node.decompose()
        text = soup.get_text(" ")
        words = re.findall(r"\b[\w’'-]+\b", text, re.UNICODE)
        return len(words)

    @staticmethod
    def _resources(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        scripts = len(soup.find_all("script", src=True))
        styles = sum(1 for l in soup.find_all("link", rel="stylesheet"))
        inline_styles = len(soup.find_all("style"))
        images = len(soup.find_all("img"))
        iframes = len(soup.find_all("iframe"))
        total_links = len(soup.find_all("a", href=True))
        size_kb = round(len(str(soup)) / 1024, 1)
        return {
            "scripts": scripts,
            "stylesheets": styles,
            "inline_styles": inline_styles,
            "images": images,
            "iframes": iframes,
            "links": total_links,
            "html_size_kb": size_kb,
            "has_viewport": soup.find("meta", attrs={"name": "viewport"}) is not None,
            "has_canonical": soup.find("link", rel="canonical") is not None,
        }

    @staticmethod
    def _links(soup: BeautifulSoup, base_url: str):
        internal: List[str] = []
        external: List[str] = []
        base = urlparse(base_url)
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or any(href.startswith(p) for p in _EXCLUDE_PATH):
                continue
            if any(href.lower().endswith(ext) for ext in _EXCLUDE_EXT):
                continue
            abs_url = urljoin(base_url, href)
            parsed = urlparse(abs_url)
            if parsed.netloc == base.netloc:
                if abs_url not in internal:
                    internal.append(abs_url)
            else:
                if abs_url not in external and parsed.scheme in ("http", "https"):
                    external.append(abs_url)
        # Limit bloat in reports
        return internal[:200], external[:100]

    @staticmethod
    def _suggestions(meta: Dict[str, str], headings: Dict[str, int]) -> List[str]:
        suggestions = []
        if not meta.get("description") or len(meta["description"]) < 50:
            suggestions.append("Meta description missing or shorter than 50 chars.")
        if not meta.get("title"):
            suggestions.append("Missing <title> tag.")
        if headings.get("h1", 0) == 0:
            suggestions.append("Page has no H1 heading.")
        elif headings.get("h1", 0) > 1:
            suggestions.append("Multiple H1 headings detected (page should have exactly one).")
        if not meta.get("viewport"):
            suggestions.append("Missing viewport meta tag (mobile optimization).")
        if "og:title" not in meta:
            suggestions.append("Missing OpenGraph og:title for social sharing.")
        return suggestions

    @staticmethod
    def _summarize(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not pages:
            return {}
        avg_words = round(sum(p["word_count"] for p in pages) / len(pages))
        avg_time = round(sum(p["response_time_ms"] for p in pages) / len(pages), 1)
        heading_counter: Counter = Counter()
        for p in pages:
            heading_counter.update(p.get("heading_counts", {}))
        return {
            "pages": len(pages),
            "avg_word_count": avg_words,
            "avg_response_ms": avg_time,
            "total_headings": dict(heading_counter),
            "pages_with_meta_description": sum(1 for p in pages if p.get("meta", {}).get("description")),
            "pages_with_h1": sum(1 for p in pages if p.get("heading_counts", {}).get("h1", 0) > 0),
        }


# Inline sanity check so the module fails loudly if its contract breaks.
def _module_import_check() -> None:
    assert SeoAuditScanner.id == "mod-seo-scanner"
    assert SeoAuditScanner.category == "SEO"
    assert SeoAuditScanner.price == 0
    assert SeoAuditScanner.price_label == "Free"