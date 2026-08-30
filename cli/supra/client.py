"""HTTP client for the Supra-Codex engine REST API.

Talks to the engine's FastAPI server (default: ``http://localhost:8000``).
Every method returns parsed JSON and raises a typed ``SupraApiError`` on
transport or non-2xx failures so the CLI can render a friendly message.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .config import Config


class SupraApiError(Exception):
    """Raised when the engine API cannot be reached or returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SupraClient:
    """Minimal, dependency-free client for the engine's REST endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout

    @classmethod
    def from_config(cls, config: Config) -> "SupraClient":
        return cls(config.api_base_url, config.timeout_seconds)

    # -- transport -----------------------------------------------------
    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = httpx.request(
                method, url, timeout=self._timeout, **kwargs
            )
        except httpx.HTTPError as exc:  # timeout, connection refused, etc.
            raise SupraApiError(
                f"Could not reach the Supra-Codex engine at {self.base_url} "
                f"({exc.__class__.__name__}). Is the API running?"
            ) from exc

        if resp.status_code >= 400:
            detail = ""
            try:
                body = resp.json()
                detail = body.get("detail", "") if isinstance(body, dict) else str(body)
            except ValueError:
                detail = resp.text[:300]
            raise SupraApiError(
                detail or f"Request failed with HTTP {resp.status_code}",
                status_code=resp.status_code,
            )

        try:
            return resp.json()
        except ValueError:
            return resp.text

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("POST", path, json=payload or {})

    # -- endpoints -----------------------------------------------------
    def health(self) -> Dict[str, Any]:
        return self.get("/health")

    def status(self) -> Dict[str, Any]:
        return self.get("/api/v1/status")

    def engine_start(self) -> Dict[str, Any]:
        return self.post("/api/v1/engine/start")

    def engine_stop(self) -> Dict[str, Any]:
        return self.post("/api/v1/engine/stop")

    def submit_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return self.post("/api/v1/tasks", task)

    def get_task(self, task_id: str) -> Dict[str, Any]:
        return self.get(f"/api/v1/tasks/{task_id}")

    def run_pipeline(self, url: str, prompt: Optional[str] = None,
                     model: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"url": url}
        if prompt:
            payload["prompt"] = prompt
        if model:
            payload["xerebro_model"] = model
        return self.post("/api/v1/pipelines/run", payload)

    def list_nodes(self) -> Dict[str, Any]:
        return self.get("/api/v1/nodes")

    def list_marketplace_modules(self) -> List[Dict[str, Any]]:
        data = self.get("/api/marketplace/modules")
        return data if isinstance(data, list) else []

    def search_marketplace(self, query: str) -> List[Dict[str, Any]]:
        modules = self.list_marketplace_modules()
        q = query.lower()
        return [
            m for m in modules
            if q in m.get("name", "").lower()
            or q in m.get("description", "").lower()
            or q in m.get("category", "").lower()
            or q in m.get("author", "").lower()
        ]

    def get_module(self, module_id: str) -> Dict[str, Any]:
        return self.get(f"/api/marketplace/modules/{module_id}")

    def install_module(self, module_id: str) -> Dict[str, Any]:
        return self.post(f"/api/marketplace/modules/{module_id}/install")

    def uninstall_module(self, module_id: str) -> Dict[str, Any]:
        return self.post(f"/api/marketplace/modules/{module_id}/uninstall")

    def list_installed_modules(self) -> List[Dict[str, Any]]:
        data = self.get("/api/marketplace/installed")
        return data if isinstance(data, list) else []
