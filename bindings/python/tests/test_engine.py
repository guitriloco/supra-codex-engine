"""
Bindings — Tests for Python WraithEngine
"""

import pytest
import json
from wraith.engine import WraithEngine, TaskConfig, TaskResult


@pytest.fixture
def engine():
    e = WraithEngine(max_workers=2)
    e.start()
    yield e
    e.stop()


def test_engine_create_and_destroy():
    """Test engine lifecycle."""
    e = WraithEngine()
    assert not e.is_running()

    e.start()
    assert e.is_running()

    e.stop()
    assert not e.is_running()


def test_submit_and_execute(engine):
    """Test submitting a task and getting results."""
    config = TaskConfig(
        type="scrape",
        target="https://httpbin.org/html",
        priority=5,
    )
    future = engine.submit_task(config)
    result = future.result(timeout=15)

    assert result.success, f"Scrape failed: {result.error_message}"
    assert result.data is not None

    data = json.loads(result.data)
    assert "url" in data
    assert data["url"] == "https://httpbin.org/html"


def test_unknown_module(engine):
    """Test task with unknown module type."""
    config = TaskConfig(
        type="nonexistent",
        target="test",
    )
    future = engine.submit_task(config)
    result = future.result(timeout=5)

    assert not result.success
    assert "Unknown module" in result.error_message


def test_custom_module(engine):
    """Test custom module registration."""
    called = False

    def custom_handler(config: TaskConfig) -> TaskResult:
        nonlocal called
        called = True
        return TaskResult(success=True, data="custom_handled")

    engine.register_module("custom", custom_handler)

    config = TaskConfig(type="custom")
    future = engine.submit_task(config)
    result = future.result(timeout=5)

    assert called
    assert result.success
    assert result.data == "custom_handled"


def test_engine_not_running():
    """Test task submission when engine is stopped."""
    e = WraithEngine()
    config = TaskConfig(type="scrape")
    future = e.submit_task(config)
    result = future.result(timeout=5)

    assert not result.success
    assert "not running" in result.error_message.lower()


def test_engine_stats(engine):
    """Test engine statistics reporting."""
    stats = engine.get_stats()
    assert stats["running"] is True


def test_scrape_convenience_method(engine):
    """Test the convenience scrape(url) method."""
    result = engine.scrape("https://httpbin.org/html", timeout_seconds=15)

    assert result.success, f"Scrape failed: {result.error_message}"

    data = json.loads(result.data)
    assert data["url"] == "https://httpbin.org/html"
    assert data["status_code"] == 200
    assert "content_type" in data


def test_scrape_extracts_html_title(engine):
    """Test that HTML title extraction works."""
    result = engine.scrape("https://httpbin.org/html", timeout_seconds=15)

    assert result.success
    data = json.loads(result.data)
    # httpbin's HTML page has a title
    assert "title" in data
    assert "body_text" in data


def test_scrape_invalid_url(engine):
    """Test scraping an invalid URL returns error."""
    result = engine.scrape("https://this-domain-does-not-exist-xyz.com", timeout_seconds=10)

    assert not result.success
    data = json.loads(result.data)
    assert "error" in data


def test_extract_title():
    """Test static title extraction."""
    html = "<html><head><title>Test Page</title></head><body>Hello</body></html>"
    title = WraithEngine._extract_title(html)
    assert title == "Test Page"


def test_extract_body_text():
    """Test static body text extraction."""
    html = "<html><body><h1>Hello</h1><p>World</p><script>alert('x')</script></body></html>"
    text = WraithEngine._extract_body_text(html)
    assert "Hello" in text
    assert "World" in text
    assert "alert" not in text  # Script content stripped