"""
Nectar Marketplace Modules — real, working scraper modules.

Each module is a ``ScraperModule`` subclass that knows how to fetch a page,
parse its HTML into structured data, and expose itself to the WraithEngine
task dispatcher so it can be run via ``POST /api/v1/tasks`` (type = module id).

Registered modules can also be consumed by the dashboard / pipeline layer via
:func:`register_modules` which installs a handler for each module in a
WraithEngine instance.
"""

from .base import ScraperModule, register_modules, MODULE_CLASSES  # noqa: F401
from .amazon_tracker import AmazonPriceTracker  # noqa: F401
from .linkedin_profiler import LinkedInCompanyProfiler  # noqa: F401
from .seo_scanner import SeoAuditScanner  # noqa: F401

# Build catalog metadata from the auto-registered module classes.
# Importing the modules above populates MODULE_CLASSES via __init_subclass__.
MODULE_METADATA = [cls().metadata() for cls in MODULE_CLASSES.values()]

__all__ = [
    "ScraperModule",
    "register_modules",
    "MODULE_CLASSES",
    "MODULE_METADATA",
    "AmazonPriceTracker",
    "LinkedInCompanyProfiler",
    "SeoAuditScanner",
]