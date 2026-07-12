"""
WraithEngine — Python Reference Implementation

Pure-Python implementation that mirrors the C++ WraithEngine API.
When pybind11 bindings are built, this module will be replaced with:

    from _wraith import WraithEngine, TaskConfig, TaskResult

For now, this reference implementation allows Python scripts to
develop against the API without needing to compile C++.
"""

import json
import uuid
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List
from concurrent.futures import Future, ThreadPoolExecutor

logger = logging.getLogger("wraith")


@dataclass
class TaskConfig:
    """Configuration for a single task. Mirrors C++ wraith::TaskConfig."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "custom"
    target: str = ""
    payload: str = ""
    priority: int = 1
    max_retries: int = 0
    timeout_seconds: int = 30


@dataclass
class TaskResult:
    """Result of a task execution. Mirrors C++ wraith::TaskResult."""
    success: bool = False
    data: str = ""
    execution_time_ms: float = 0.0
    error_message: str = ""
    exit_code: int = 0


class WraithEngine:
    """
    Python reference implementation of WraithEngine.

    Mirrors the C++ engine's public API. Will be replaced by
    pybind11 native bindings for production use.

    Usage:
        engine = WraithEngine()
        engine.start()

        # Via task API:
        future = engine.submit_task(TaskConfig(type="scrape", target="https://example.com"))
        result = future.result()

        # Convenience method:
        result = engine.scrape("https://example.com")
    """

    def __init__(self, max_workers: int = 4):
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._running = False
        self._modules: Dict[str, Callable[[TaskConfig], TaskResult]] = {}
        self._stats = {
            "running": False,
            "queue_size": 0,
            "active_workers": 0,
            "memory_mb": 0.0,
            "cpu_percent": 0.0,
        }
        logger.info("WraithEngine (Python ref) initialized with %d workers", max_workers)

        # Register built-in modules
        self._register_default_modules()

    def _register_default_modules(self):
        """Register the built-in task handler modules."""
        self.register_module("scrape", self._http_scrape)
        self.register_module("enrich", self._data_enrich)
        self.register_module("rate_limit", self._rate_limit_check)

    def start(self):
        """Start the engine."""
        self._running = True
        self._stats["running"] = True
        logger.info("WraithEngine started")

    def stop(self):
        """Stop the engine gracefully."""
        self._running = False
        self._pool.shutdown(wait=False)
        self._stats["running"] = False
        logger.info("WraithEngine stopped")

    # ──────────────────────────────────────────────────────────────────────────
    # Convenience: direct scrape(url) — the primary user-facing method
    # ──────────────────────────────────────────────────────────────────────────

    def scrape(self, url: str, timeout_seconds: int = 30) -> TaskResult:
        """
        Fetch a URL and extract its text content.

        This is the primary convenience method for scraping. It submits a
        scrape task and blocks until the result is available.

        Args:
            url: The URL to scrape.
            timeout_seconds: Maximum time to wait for the HTTP request.

        Returns:
            TaskResult with scraped text content in .data (JSON-encoded).

        Example:
            result = engine.scrape("https://example.com")
            print(result.data)
        """
        config = TaskConfig(
            type="scrape",
            target=url,
            timeout_seconds=timeout_seconds,
        )
        future = self.submit_task(config)
        return future.result(timeout=timeout_seconds + 10)

    # ──────────────────────────────────────────────────────────────────────────
    # Task API
    # ──────────────────────────────────────────────────────────────────────────

    def submit_task(self, config: TaskConfig) -> Future:
        """
        Submit a task for asynchronous execution.

        Returns a concurrent.futures.Future that resolves to a TaskResult.
        """
        if not self._running:
            future = Future()
            future.set_result(TaskResult(
                success=False,
                error_message="Engine not running",
                exit_code=-1,
            ))
            return future

        logger.debug("Submitting task: %s [%s]", config.id, config.type)
        return self._pool.submit(self._execute_task, config)

    def register_module(self, name: str, handler: Callable[[TaskConfig], TaskResult]):
        """Register a custom module by name."""
        self._modules[name] = handler
        logger.debug("Module '%s' registered", name)

    def get_stats(self) -> Dict[str, Any]:
        """Get current engine statistics."""
        return {**self._stats}

    def is_running(self) -> bool:
        """Check if the engine is running."""
        return self._running

    # ──────────────────────────────────────────────────────────────────────────
    # Internal execution
    # ──────────────────────────────────────────────────────────────────────────

    def _execute_task(self, config: TaskConfig) -> TaskResult:
        """Execute a task by dispatching to the appropriate module."""
        start_time = time.time()

        handler = self._modules.get(config.type)
        if not handler:
            return TaskResult(
                success=False,
                error_message=f"Unknown module type: {config.type}",
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Retry loop
        last_error = ""
        for attempt in range(config.max_retries + 1):
            try:
                result = handler(config)
                result.execution_time_ms = (time.time() - start_time) * 1000
                return result
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Task %s attempt %d failed: %s",
                    config.id, attempt + 1, last_error,
                )
                time.sleep(0.5)  # Backoff between retries

        return TaskResult(
            success=False,
            error_message=f"All {config.max_retries + 1} attempts failed: {last_error}",
            exit_code=-1,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Built-in modules
    # ──────────────────────────────────────────────────────────────────────────

    def _http_scrape(self, config: TaskConfig) -> TaskResult:
        """
        Built-in HTTP scraper module.

        Fetches the target URL using httpx, extracts meaningful text content
        (title + body text for HTML pages, raw response for others), and
        returns it as JSON.
        """
        import httpx
        from httpx import HTTPError, RequestError

        logger.info("Scraping URL: %s", config.target)

        try:
            resp = httpx.get(
                config.target,
                follow_redirects=True,
                timeout=config.timeout_seconds,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; Supra-Codex-Engine/0.1.0; "
                        "+https://supra-codex.io)"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
            )
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "").lower()
            content = resp.text

            # Attempt to extract meaningful text from HTML
            extracted = {
                "url": config.target,
                "status_code": resp.status_code,
                "content_type": content_type,
                "content_length": len(content),
                "text": content,
                "headers": dict(resp.headers),
            }

            # If HTML, try to pull title and readable text
            if "text/html" in content_type:
                extracted["title"] = self._extract_title(content)
                extracted["body_text"] = self._extract_body_text(content)

            return TaskResult(
                success=True,
                data=json.dumps(extracted, ensure_ascii=False),
            )

        except HTTPError as e:
            logger.error("HTTP error scraping %s: %s", config.target, str(e))
            return TaskResult(
                success=False,
                data=json.dumps({"url": config.target, "error": str(e)}),
                error_message=str(e),
                exit_code=1,
            )
        except Exception as e:
            logger.error("Unexpected error scraping %s: %s", config.target, str(e))
            return TaskResult(
                success=False,
                data=json.dumps({"url": config.target, "error": str(e)}),
                error_message=str(e),
                exit_code=2,
            )

    @staticmethod
    def _extract_title(html: str) -> str:
        """Extract <title> tag content from HTML."""
        import re
        match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_body_text(html: str) -> str:
        """Extract readable body text from HTML by stripping tags."""
        import re
        # Remove scripts and styles
        cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.IGNORECASE | re.DOTALL)
        # Remove all other HTML tags
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        # Collapse whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # Truncate to a reasonable size (first 50KB)
        max_chars = 50000
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "... [truncated]"
        return cleaned

    def _data_enrich(self, config: TaskConfig) -> TaskResult:
        """Built-in data enrichment module."""
        return TaskResult(
            success=True,
            data=f'{{"enriched": "{config.payload}", "status": "stub"}}',
        )

    def _rate_limit_check(self, config: TaskConfig) -> TaskResult:
        """Built-in rate limiter module."""
        return TaskResult(
            success=True,
            data='{"allowed": true}',
        )


# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ──────────────────────────────────────────────────────────────────────────────

_default_engine: Optional[WraithEngine] = None


def get_engine() -> WraithEngine:
    """Get or create the default WraithEngine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = WraithEngine()
    return _default_engine