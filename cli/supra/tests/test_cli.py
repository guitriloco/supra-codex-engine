"""End-to-end smoke tests for the CLI's Typer commands.

These mock the SupraClient so no live engine is required. They verify the
CLI wires the right commands, parses output, and exits cleanly.
"""

from __future__ import annotations

from typer.testing import CliRunner

from supra.cli import app

runner = CliRunner()


class FakeClient:
    def __init__(self):
        self.calls = []
        self.base_url = "http://localhost:8000"

    def health(self):
        self.calls.append("health")
        return {"status": "ok", "engine": "running", "xerebro": True, "version": "0.1.0"}

    def status(self):
        self.calls.append("status")
        return {"engine": "WraithEngine", "version": "0.1.0", "running": True,
                "stats": {"tasks_submitted": 5, "tasks_completed": 4}}

    def run_pipeline(self, url, prompt=None, model=None):
        self.calls.append(("run_pipeline", url))
        return {
            "pipeline_id": "abc123",
            "url": url,
            "status": "success",
            "total_duration_ms": 1234.5,
            "steps": [{"step": "scrape", "status": "success", "duration_ms": 300,
                       "result_summary": "fetched"}],
            "scraped_content": {"title": "Example", "body_text": "hello world"},
            "xerebro_analysis": {"summary": "done"},
            "xerebro_available": True,
        }

    def list_nodes(self):
        self.calls.append("list_nodes")
        return {"nodes": [{"id": "n1", "hostname": "node-a", "region": "us",
                           "capabilities": ["scrape"], "cpu": 10.0, "ram": 256.0,
                           "task_count": 3, "status": "online"}], "count": 1, "online": 1}

    def search_marketplace(self, query):
        self.calls.append(("search", query))
        return [{"id": "m1", "name": "Price Monitor", "category": "ecommerce",
                 "author": "nectar", "rating": 4.5, "downloads": 100,
                 "price_label": "Free", "installed": False}]

    def install_module(self, module_id):
        self.calls.append(("install", module_id))
        return {"message": f"Module '{module_id}' installed successfully", "module_id": module_id}


def _with_fake(monkeypatch):
    fake = FakeClient()
    import supra.cli as cli_mod
    monkeypatch.setattr(cli_mod, "_client", lambda: fake)
    return fake


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("status", "scrape", "pipeline", "nodes", "marketplace", "config"):
        assert cmd in result.output


def test_status_command(monkeypatch):
    _with_fake(monkeypatch)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Supra-Codex Engine" in result.output


def test_pipeline_run(monkeypatch):
    _with_fake(monkeypatch)
    result = runner.invoke(app, ["pipeline", "run", "https://example.com"])
    assert result.exit_code == 0
    assert "Status: success" in result.output
    assert "Total:" in result.output


def test_pipeline_run_json(monkeypatch):
    _with_fake(monkeypatch)
    result = runner.invoke(app, ["pipeline", "run", "https://example.com", "--json"])
    assert result.exit_code == 0
    assert '"pipeline_id": "abc123"' in result.output


def test_nodes_list(monkeypatch):
    _with_fake(monkeypatch)
    result = runner.invoke(app, ["nodes", "list"])
    assert result.exit_code == 0
    assert "node-a" in result.output
    assert "1 total" in result.output


def test_marketplace_search(monkeypatch):
    _with_fake(monkeypatch)
    result = runner.invoke(app, ["marketplace", "search", "price"])
    assert result.exit_code == 0
    assert "Price Monitor" in result.output


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "supra-codex" in result.output
