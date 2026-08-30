#!/usr/bin/env python3
"""
Supra-Codex Engine — Virtual Worker Node Simulator

Spawns 3–5 virtual worker nodes in separate threads. Each node:
  1. Registers with the API (POST /api/v1/nodes/register)
  2. Sends heartbeats every ~10s (POST /api/v1/nodes/{id}/heartbeat)
  3. Polls for dispatched tasks (GET /api/v1/nodes/{id}/tasks)
  4. Executes scrape tasks locally via httpx
  5. Submits results back (POST /api/v1/nodes/{id}/tasks/{task_id}/result)

Usage:
    python scripts/simulate_nodes.py [--api-url http://localhost:8000] [--count 4]
"""

import argparse
import json
import logging
import random
import signal
import sys
import threading
import time
from typing import Optional, Dict, Any

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)-20s] %(levelname)s  %(message)s",
)
logger = logging.getLogger("simulate-nodes")

# Node definitions — each tuple: (hostname, region, capabilities)
NODE_DEFINITIONS = [
    ("node-alpha-01", "us-east",    ["scrape", "enrich"]),
    ("node-beta-02",  "eu-west",    ["scrape"]),
    ("node-gamma-03", "ap-southeast", ["scrape", "transform"]),
    ("node-delta-04", "us-west",    ["scrape", "enrich", "transform"]),
    ("node-epsilon-05", "eu-central", ["scrape"]),
]

STOP_EVENT = threading.Event()


def handle_signal(signum, frame):
    logger.info("Received signal %s — shutting down nodes...", signum)
    STOP_EVENT.set()


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


# ---------------------------------------------------------------------------
# Worker Node (runs in its own thread)
# ---------------------------------------------------------------------------

class VirtualNode(threading.Thread):
    """Simulated compute node that registers, heartbeats, and executes tasks."""

    def __init__(
        self,
        hostname: str,
        region: str,
        capabilities: list[str],
        api_url: str,
        heartbeat_interval: float = 10.0,
        poll_interval: float = 2.0,
    ):
        super().__init__(name=hostname, daemon=True)
        self.hostname = hostname
        self.region = region
        self.capabilities = capabilities
        self.api_url = api_url.rstrip("/")
        self.heartbeat_interval = heartbeat_interval
        self.poll_interval = poll_interval
        self.port = 0  # simulated
        self._http: Optional[httpx.Client] = None
        self._registered = False

    # ---- HTTP helpers ----

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=httpx.Timeout(15.0))
        return self._http

    def _post(self, path: str, json_body: dict) -> dict:
        resp = self.http.post(f"{self.api_url}{path}", json=json_body)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str) -> dict:
        resp = self.http.get(f"{self.api_url}{path}")
        resp.raise_for_status()
        return resp.json()

    # ---- Lifecycle ----

    def register(self):
        """Register this node with the API."""
        payload = {
            "hostname": self.hostname,
            "capabilities": self.capabilities,
            "cpu": round(random.uniform(5.0, 80.0), 1),
            "ram": round(random.uniform(64.0, 2048.0), 1),
            "region": self.region,
            "port": self.port,
        }
        try:
            result = self._post("/api/v1/nodes/register", payload)
            self._registered = True
            logger.info("Registered — node_id=%s status=%s", result.get("node_id"), result.get("status"))
        except Exception as exc:
            logger.error("Registration failed: %s", exc)

    def heartbeat(self):
        """Send a heartbeat ping with current resource usage."""
        payload = {
            "cpu": round(random.uniform(5.0, 80.0), 1),
            "ram": round(random.uniform(64.0, 2048.0), 1),
            "task_count": 0,  # simplified — could track active tasks
        }
        try:
            self._post(f"/api/v1/nodes/{self.hostname}/heartbeat", payload)
            logger.debug("Heartbeat sent (cpu=%.1f%%, ram=%.0fMB)", payload["cpu"], payload["ram"])
        except Exception as exc:
            logger.warning("Heartbeat failed: %s", exc)

    def poll_tasks(self) -> list[dict]:
        """Check for pending dispatch tasks."""
        try:
            result = self._get(f"/api/v1/nodes/{self.hostname}/tasks")
            return result.get("tasks", [])
        except Exception as exc:
            logger.warning("Task poll failed: %s", exc)
            return []

    def execute_scrape(self, url: str) -> Dict[str, Any]:
        """Scrape a URL locally using httpx (mirrors WraithEngine.scrape)."""
        try:
            resp = self.http.get(url, follow_redirects=True)
            content_type = resp.headers.get("content-type", "")
            body = resp.text

            # Extract title
            import re
            title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""

            # Extract body text (strip script/style tags)
            body_clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", body, flags=re.IGNORECASE | re.DOTALL)
            body_text = re.sub(r"<[^>]+>", "", body_clean)
            body_text = re.sub(r"\s+", " ", body_text).strip()[:50000]

            return {
                "title": title,
                "body_text": body_text,
                "status_code": resp.status_code,
                "content_type": content_type,
            }
        except Exception as exc:
            logger.error("Scrape failed for %s: %s", url, exc)
            raise

    def submit_result(self, task_id: str, status: str, scraped_data: Optional[dict] = None, error: Optional[str] = None):
        """Submit a task result back to the API."""
        payload = {
            "task_id": task_id,
            "status": status,
            "scraped_data": scraped_data,
            "error": error,
        }
        try:
            self._post(f"/api/v1/nodes/{self.hostname}/tasks/{task_id}/result", payload)
            logger.info("Task %s completed: %s", task_id, status)
        except Exception as exc:
            logger.error("Failed to submit result for %s: %s", task_id, exc)

    # ---- Main loop ----

    def run(self):
        logger.info("Node starting (region=%s, capabilities=%s)", self.region, self.capabilities)
        self.register()

        last_heartbeat = 0.0

        while not STOP_EVENT.is_set():
            now = time.time()

            # Heartbeat every heartbeat_interval seconds
            if now - last_heartbeat >= self.heartbeat_interval:
                self.heartbeat()
                last_heartbeat = now

            # Poll for dispatch tasks
            tasks = self.poll_tasks()
            for task in tasks:
                task_id = task.get("task_id")
                url = task.get("url")
                logger.info("Received task %s: scrape %s", task_id, url)
                try:
                    data = self.execute_scrape(url)
                    self.submit_result(task_id, "success", scraped_data=data)
                except Exception as exc:
                    self.submit_result(task_id, "failed", error=str(exc))

            time.sleep(self.poll_interval)

        logger.info("Node stopped")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Supra-Codex virtual worker node simulator")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API server base URL")
    parser.add_argument("--count", type=int, default=4, choices=range(1, 6),
                        help="Number of virtual nodes to spawn (1–5)")
    parser.add_argument("--heartbeat", type=float, default=10.0, help="Heartbeat interval in seconds")
    parser.add_argument("--poll", type=float, default=2.0, help="Task poll interval in seconds")
    args = parser.parse_args()

    # Select node definitions
    nodes_config = NODE_DEFINITIONS[: args.count]

    logger.info("Starting %d virtual worker nodes → %s", args.count, args.api_url)
    logger.info("Heartbeat: %.0fs | Poll: %.0fs", args.heartbeat, args.poll)

    threads = []
    for hostname, region, capabilities in nodes_config:
        node = VirtualNode(
            hostname=hostname,
            region=region,
            capabilities=capabilities,
            api_url=args.api_url,
            heartbeat_interval=args.heartbeat,
            poll_interval=args.poll,
        )
        node.start()
        threads.append(node)
        time.sleep(0.3)  # stagger registration

    logger.info("All nodes started. Press Ctrl+C to stop.")

    # Wait for stop signal
    try:
        while not STOP_EVENT.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    logger.info("Waiting for nodes to shut down...")
    for t in threads:
        t.join(timeout=5)
    logger.info("Simulator stopped")


if __name__ == "__main__":
    main()