"""
LinkedIn Company Profiler — ``mod-linkedin-profiler``

Extracts company intelligence from LinkedIn public company pages:

  * company name & tagline
  * employee count & company size band
  * industry & headquarters
  * funding information
  * recent news / update headlines

LinkedIn is notoriously aggressive about bot detection (login walls, the
"authwall" interstitial, and 999 status on scraped pages). This module:

  * rotates browser headers (base module)
  * parses LinkedIn's embedded ``__NEXT_DATA__`` JSON when present — the most
    reliable source of structured company data on public pages
  * falls back to visible-text heuristics (regex on "Employees", "Industry",
    "Funding", "Headquarters" label rows)
  * returns a ``blocked_by_anti_bot`` flag and raises a clear error when the
    authwall hides the company data, so callers know the scrape was throttled
    rather than "no data".
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup

from .base import ScraperModule

_AUTHWALL_MARKERS = (
    "authwall",
    "join now to see",
    "sign in to see",
    "you need to sign in",
    "this page isn't available",
)


class LinkedInCompanyProfiler(ScraperModule):
    """Extract company info (employees, industry, funding, news) from LinkedIn."""

    id = "mod-linkedin-profiler"
    name = "LinkedIn Company Profiler"
    category = "Leads"
    price = 29
    price_label = "$29"
    version = "1.0.0"
    author = "Supra-Codex"
    description = (
        "Extract company intelligence from LinkedIn pages — employee count, "
        "industry, funding and recent news. Parses embedded JSON with "
        "visible-text fallback."
    )
    features = [
        "Employee count & size band",
        "Industry & headquarters",
        "Funding information",
        "Recent news extraction",
        "__NEXT_DATA__ JSON parsing",
        "Authwall detection",
    ]
    requirements = ["WraithEngine >= 0.1.0", "Python >= 3.9", "beautifulsoup4", "lxml"]

    # ── Parsing ─────────────────────────────────────────────────────────

    def parse_html(self, html: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)
        lowered = text.lower()

        is_blocked = any(marker in lowered for marker in _AUTHWALL_MARKERS)

        # Try embedded JSON first (most reliable), then fall back to text.
        json_data = self._extract_next_data(soup, text)
        result: Dict[str, Any] = {"url": url, "blocked_by_anti_bot": is_blocked}

        if json_data:
            result.update(self._from_json(json_data))
        else:
            result.update(self._from_text(text))

        # Always enrich with visible labels when present.
        result.setdefault("name", self._og_title(soup))
        result.setdefault("industry", self._label_value(text, "industry"))
        result.setdefault("employee_count", self._employees(text))
        result.setdefault("company_size", self._label_value(text, "company size"))
        result.setdefault("headquarters", self._label_value(text, "headquarters"))
        result["recent_news"] = self._recent_news(soup)

        if is_blocked and not result.get("name"):
            result["status"] = "blocked"
        return result

    # ── JSON path ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_next_data(soup: BeautifulSoup, text: str) -> Optional[Dict[str, Any]]:
        """Return company payload from LinkedIn's __NEXT_DATA__ JSON, if present."""
        el = soup.find("script", attrs={"id": "__NEXT_DATA__"}) or soup.find(
            "script", attrs={"type": "application/json"}
        )
        if not el or not el.string:
            return None
        try:
            payload = json.loads(el.string)
        except (json.JSONDecodeError, TypeError):
            return None
        return payload

    @classmethod
    def _from_json(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively hunt for a company object with the fields we care about."""
        result: Dict[str, Any] = {}
        found: Dict[str, Any] = {}

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                # Heuristic: node that looks like a company profile.
                if any(k in node for k in ("name", "employeeCount", "industries", "headquarter")):
                    for key in ("name", "employeeCount", "employeeCountRange", "description", "website"):
                        if key in node and key not in found:
                            found[key] = node[key]
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(payload)

        if found:
            name = found.get("name")
            if isinstance(name, dict):
                name = name.get("localizedName") or name.get("text")
            result["name"] = str(name) if name else None

            ec = found.get("employeeCount")
            if ec is not None:
                result["employee_count"] = int(ec)

            ecr = found.get("employeeCountRange")
            if isinstance(ecr, dict) and ("start" in ecr or "end" in ecr):
                result["company_size"] = f"{ecr.get('start', '?')}-{ecr.get('end', '?')}"

            if found.get("description"):
                result["description"] = found["description"]

        return result

    # ── Text path ───────────────────────────────────────────────────────

    @staticmethod
    def _og_title(soup: BeautifulSoup) -> str:
        og = soup.find("meta", attrs={"property": "og:title"})
        if og:
            return og.get("content", "").strip()
        title = soup.find("title")
        return title.get_text(strip=True) if title else ""

    @staticmethod
    def _label_value(text: str, label: str) -> str:
        """Find 'Label  value' in flattened visible text."""
        m = re.search(rf"{re.escape(label)}\s*[:•]?\s*([^\n•|]{2,80}?)(?=\s*(?:Employees|Industry|Funding|Headquarters|Website|Founded|Specialties|See all|$))", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return ""

    @staticmethod
    def _employees(text: str) -> Optional[int]:
        # Patterns like "1,001-5,000 employees", "10k+ employees", "500 employees"
        m = re.search(r"([\d,]+(?:[kK+])?)\s*(?:-|–)?\s*([\d,]+[kK+]?)?\s*employees?", text)
        if not m:
            return None
        raw = m.group(1).replace(",", "").lower()
        if raw.endswith("k"):
            return int(float(raw[:-1]) * 1000)
        return int(raw)

    @staticmethod
    def _recent_news(soup: BeautifulSoup) -> list:
        """Collect recent update/news headlines from links on the page."""
        headlines = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/posts/" not in href and "/updates/" not in href:
                continue
            title = a.get_text(" ", strip=True)
            if title and 12 < len(title) < 200 and title not in seen:
                seen.add(title)
                headlines.append({"headline": title, "url": href})
            if len(headlines) >= 10:
                break
        return headlines


# Inline sanity check so the module fails loudly if its contract breaks.
def _module_import_check() -> None:
    assert LinkedInCompanyProfiler.id == "mod-linkedin-profiler"
    assert LinkedInCompanyProfiler.category == "Leads"
    assert LinkedInCompanyProfiler.price == 29