"""Tests for the Supra-Codex CLI client module (no live API required)."""

from __future__ import annotations

import json

import pytest

from supra.config import Config
from supra.client import SupraClient, SupraApiError


def test_config_defaults(tmp_path):
    cfg = Config(tmp_path / "config.json")
    assert cfg.api_base_url == "http://localhost:8000"
    assert cfg.timeout_seconds == 60.0


def test_config_set_and_persist(tmp_path):
    path = tmp_path / "config.json"
    cfg = Config(path)
    cfg.set("api_base_url", "http://10.0.0.5:9000")
    cfg.set("timeout_seconds", "120")
    reloaded = Config(path)
    assert reloaded.api_base_url == "http://10.0.0.5:9000"
    assert reloaded.timeout_seconds == 120.0


def test_config_resilient_to_corrupt_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ not json !!", encoding="utf-8")
    cfg = Config(path)
    assert cfg.api_base_url == "http://localhost:8000"


def test_client_base_url_normalized():
    c = SupraClient("http://localhost:8000/")
    assert c.base_url == "http://localhost:8000"


def test_run_pipeline_payload():
    c = SupraClient("http://localhost:8000")
    # Check payload shape via a mocked request
    import supra.client as client_mod
    captured = {}

    def fake_request(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs.get("json")
        return {"ok": True}

    c._request = fake_request
    c.run_pipeline("https://example.com", prompt="Extract price", model="llama3.2")
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v1/pipelines/run"
    assert captured["json"] == {
        "url": "https://example.com",
        "prompt": "Extract price",
        "xerebro_model": "llama3.2",
    }


def test_search_marketplace_filters():
    c = SupraClient("http://localhost:8000")
    modules = [
        {"id": "price-monitor", "name": "Price Monitor", "category": "ecommerce",
         "author": "nectar", "description": "Track product prices"},
        {"id": "lead-gen", "name": "Lead Gen Bot", "category": "leads",
         "author": "nectar", "description": "Find leads"},
    ]
    c.list_marketplace_modules = lambda: modules
    results = c.search_marketplace("price")
    assert [m["id"] for m in results] == ["price-monitor"]
    results = c.search_marketplace("nectar")
    assert len(results) == 2


def test_api_error_raises():
    c = SupraClient("http://localhost:8000")

    def fake_request(method, path, **kwargs):
        raise SupraApiError("Could not reach the Supra-Codex engine", status_code=None)

    c._request = fake_request
    with pytest.raises(SupraApiError):
        c.health()
