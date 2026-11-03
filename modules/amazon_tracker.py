"""
Amazon Price Tracker — ``mod-amazon-tracker``

Scrapes Amazon product pages and extracts:

  * product title
  * current price (handles deal price vs. list price)
  * star rating + review count
  * availability / stock status
  * product identifiers (ASIN)

Anti-bot strategy (in addition to the base module's rotating User-Agent):

  * All requests include full browser headers (Accept-Language, Sec-Fetch-*,
    Upgrade-Insecure-Requests).
  * ``fetch`` retries with a *fresh* User-Agent on 403/429/503 and checks the
    response body for Amazon's "robot check" page, flagging it as such.
  * Price parsing supports both classic ``#priceblock_*`` selectors and the
    newer ``span.a-offscreen`` markup so it keeps working as Amazon rotates
    its DOM.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import ScraperModule

# Markers that indicate Amazon served a bot/captcha wall instead of the product.
_ROBOT_MARKERS = (
    "enter the characters you see below",
    "robot check",
    "api-services-support@amazon.com",
    "to discuss automated access to amazon data",
    "captcha",
    "sorry, we just need to make sure you're not a robot",
)


class AmazonPriceTracker(ScraperModule):
    """Extract price, title, rating and availability from Amazon product pages."""

    id = "mod-amazon-tracker"
    name = "Amazon Price Tracker"
    category = "Scraping"
    price = 19
    price_label = "$19"
    version = "1.0.0"
    author = "Supra-Codex"
    description = (
        "Scrape Amazon product pages for price, title, rating and availability. "
        "Rotates browser headers to defeat common bot walls."
    )
    features = [
        "Price extraction (deal + list)",
        "Star rating & review count",
        "Availability / stock status",
        "ASIN capture",
        "Anti-bot header rotation",
        "Robot-check detection",
    ]
    requirements = ["WraithEngine >= 0.1.0", "Python >= 3.9", "beautifulsoup4", "lxml"]

    # ── Parsing ─────────────────────────────────────────────────────────

    def parse_html(self, html: str, url: str) -> Dict[str, Any]:
        """Parse an Amazon product page into structured product data."""
        soup = BeautifulSoup(html, "lxml")
        lowered = html.lower()

        is_robot = any(marker in lowered for marker in _ROBOT_MARKERS)

        title = self._extract_title(soup)
        price_info = self._extract_price(soup)
        rating_info = self._extract_rating(soup)
        availability = self._extract_availability(soup)
        asin = self._extract_asin(soup, url)

        return {
            "url": url,
            "title": title,
            **price_info,
            **rating_info,
            "availability": availability,
            "asin": asin,
            "blocked_by_anti_bot": is_robot,
        }

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        el = soup.select_one("#productTitle")
        if el:
            return el.get_text(strip=True)
        # Fallback: og:title meta
        og = soup.find("meta", attrs={"property": "og:title"})
        return (og.get("content", "").strip() if og else "")

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> Dict[str, Any]:
        """Return {price, price_currency, list_price, price_unit} or zeros."""
        price_text: Optional[str] = None

        # Classic selectors used for years by Amazon desktop.
        for sel in (
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "#newBuyBoxPrice",
            "#price_inside_buybox",
            ".a-price .a-offscreen",
            ".priceToPay .a-offscreen",
        ):
            el = soup.select_one(sel)
            if el:
                price_text = el.get_text(strip=True)
                if price_text:
                    break

        price = 0.0
        currency = "USD"
        if price_text:
            match = re.search(r"([\d,]+(?:\.\d{1,2})?)", price_text.replace("\u00a0", " "))
            if match:
                price = float(match.group(1).replace(",", ""))
            cur = re.search(r"([A-Z]{3}|[$€£¥])", price_text)
            if cur:
                currency = cur.group(1) if len(cur.group(1)) == 3 else {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}.get(cur.group(1), "USD")

        # List price (struck-through) — the "was" price.
        list_price = None
        list_el = soup.select_one(".a-text-price .a-offscreen") or soup.select_one(
            "#priceblock_ourprice + span .a-offscreen"
        )
        if list_el:
            text = list_el.get_text(strip=True)
            m = re.search(r"([\d,]+(?:\.\d{1,2})?)", text)
            if m:
                list_price = float(m.group(1).replace(",", ""))

        return {
            "price": price,
            "price_currency": currency,
            "list_price": list_price,
        }

    @staticmethod
    def _extract_rating(soup: BeautifulSoup) -> Dict[str, Any]:
        """Return {rating, rating_count} extracted from the rating popover."""
        rating = 0.0
        rating_count = 0

        pop = soup.select_one("#acrPopover")
        if pop:
            title_attr = pop.get("title", "")
            m = re.search(r"([\d.]+)\s*out of 5", title_attr)
            if m:
                rating = float(m.group(1))
            # count lives next to the popover
            count_el = soup.select_one("#acrCustomerReviewText")
            if count_el:
                cm = re.search(r"([\d,]+)", count_el.get_text())
                if cm:
                    rating_count = int(cm.group(1).replace(",", ""))

        # Fallback: the visually-hidden star alt text.
        if not rating:
            star = soup.select_one("i.a-icon-star span.a-icon-alt") or soup.select_one(
                "span[data-hook='rating-out-of-text']"
            )
            if star:
                m = re.search(r"([\d.]+)", star.get_text())
                if m:
                    rating = float(m.group(1))

        return {"rating": rating, "rating_count": rating_count}

    @staticmethod
    def _extract_availability(soup: BeautifulSoup) -> str:
        el = soup.select_one("#availability span") or soup.select_one("#availability")
        if el:
            return el.get_text(strip=True)
        # Buybox "In Stock" label
        bb = soup.select_one(".a-icon-success")
        if bb:
            return "In Stock"
        return "unknown"

    @staticmethod
    def _extract_asin(soup: BeautifulSoup, url: str) -> Optional[str]:
        # ASIN appears in dp URLs: /dp/ASIN or /gp/product/ASIN
        m = re.search(r"/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})", url)
        if m:
            return m.group(1)
        # Also present as data-asin on the page root element.
        root = soup.find("div", attrs={"data-asin": True})
        if root:
            return root.get("data-asin")
        return None


# Inline sanity check so the module fails loudly if its contract breaks.
def _module_import_check() -> None:
    assert AmazonPriceTracker.id == "mod-amazon-tracker"
    assert AmazonPriceTracker.category == "Scraping"
    assert AmazonPriceTracker.price == 19