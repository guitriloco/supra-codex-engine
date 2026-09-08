"""
Supra-Codex Engine — REST API Server

FastAPI-based REST API that exposes the WraithEngine capabilities
to the orchestration dashboard and external clients.

Dashboard-compatible endpoints:
  POST /api/pipelines         — submit a pipeline run
  GET  /api/pipelines         — list pipelines
  GET  /api/pipelines/{id}    — get pipeline status
  POST /api/pipelines/{id}/pause   — pause pipeline
  POST /api/pipelines/{id}/resume  — resume pipeline
  GET  /api/nodes              — list compute nodes
  GET  /api/nodes/{name}       — get node details
  WS   /ws/pipelines           — WebSocket for live pipeline events

Also available at /api/v1/* for versioned access:
  POST /api/v1/pipelines/run   — run a pipeline with full config
  GET  /api/v1/pipelines/{pipeline_id}
  GET  /api/v1/nodes
"""

import asyncio
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("supra-api")

# Import engine and Xerebro
from wraith.engine import WraithEngine, TaskConfig
WRAITH_ENGINE = WraithEngine(max_workers=4)

from xerebro.src.brain import XerebroBrain, XerebroConfig
XEREBRO_BRAIN = XerebroBrain()

app = FastAPI(
    title="Supra-Codex Engine API",
    description="REST API for distributed AI orchestration and automation pipelines",
    version="0.1.0",
)

# CORS — allow the dashboard to connect from any origin in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# WebSocket connection manager
# ============================================================================


class ConnectionManager:
    """Manages active WebSocket connections for live pipeline events."""

    def __init__(self):
        self._connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info("WebSocket connected (%d active)", len(self._connections))
        # Send a welcome event with current engine status
        await ws.send_json({
            "type": "status",
            "pipelineId": "",
            "payload": {
                "engine": "running" if WRAITH_ENGINE.is_running() else "stopped",
                "xerebro": XEREBRO_BRAIN.is_available,
                "version": "0.1.0",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("WebSocket disconnected (%d active)", len(self._connections))

    async def broadcast_pipeline_event(
        self,
        event_type: str,
        pipeline_id: str,
        payload: Dict[str, Any],
    ):
        """Broadcast a pipeline event to all connected clients."""
        message = {
            "type": event_type,
            "pipelineId": pipeline_id,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = ConnectionManager()


# ============================================================================
# Distributed Node Registry
# ============================================================================

# node_id → {hostname, capabilities, cpu, ram, region, status, last_heartbeat, tasks}
node_registry: Dict[str, Dict[str, Any]] = {}

# Pending dispatch tasks: task_id → {url, node_id, status, result, event}
pending_dispatch: Dict[str, Dict[str, Any]] = {}

# Round-robin counter for node dispatch
_round_robin_idx = 0
_round_robin_lock = threading.Lock()

# Heartbeat timeout (seconds)
HEARTBEAT_TIMEOUT = 30


def _get_online_nodes() -> List[Dict[str, Any]]:
    """Return all currently online nodes."""
    return [
        n for nid, n in node_registry.items()
        if n.get("status") == "online"
    ]


def _round_robin_node() -> Optional[Dict[str, Any]]:
    """Select next available online node using round-robin."""
    global _round_robin_idx
    online = _get_online_nodes()
    if not online:
        return None
    with _round_robin_lock:
        idx = _round_robin_idx % len(online)
        _round_robin_idx += 1
    return online[idx]


async def _stale_node_cleanup_loop():
    """Background task: mark nodes offline if no heartbeat within HEARTBEAT_TIMEOUT seconds."""
    while True:
        await asyncio.sleep(5)
        now = time.time()
        for nid, node in list(node_registry.items()):
            last_hb = node.get("last_heartbeat", 0)
            if node.get("status") == "online" and (now - last_hb) > HEARTBEAT_TIMEOUT:
                node["status"] = "offline"
                logger.warning("Node %s marked offline — heartbeat timeout (%.0fs)", nid, now - last_hb)


# ============================================================================
# In-memory pipeline store
# ============================================================================

pipeline_store: Dict[str, Dict[str, Any]] = {}


def _store_pipeline(pipeline_id: str, data: Dict[str, Any]):
    pipeline_store[pipeline_id] = {
        **data,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _update_pipeline(pipeline_id: str, updates: Dict[str, Any]):
    if pipeline_id in pipeline_store:
        pipeline_store[pipeline_id].update(updates)
        pipeline_store[pipeline_id]["updated_at"] = datetime.now(timezone.utc).isoformat()


# ============================================================================
# Models
# ============================================================================


class TaskRequest(BaseModel):
    type: str = Field(..., description="Task type: scrape, enrich, transform, custom")
    target: str = Field("", description="URL, file path, or target identifier")
    payload: str = Field("", description="JSON or raw input data")
    priority: int = Field(1, ge=0, le=100, description="Task priority (higher = more urgent)")
    max_retries: int = Field(0, ge=0, le=10)
    timeout_seconds: int = Field(30, ge=1, le=3600)


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    engine: str
    version: str
    running: bool
    stats: Dict[str, Any]


# Pipeline models
class PipelineRunRequest(BaseModel):
    url: str = Field(..., description="The URL to scrape and process")
    prompt: Optional[str] = Field(
        None,
        description="Optional custom prompt for Xerebro AI. If omitted, a default enrichment prompt is used.",
    )
    xerebro_model: Optional[str] = Field(
        None,
        description="Override the Ollama model for this pipeline run",
    )


class PipelineStep(BaseModel):
    step: str
    status: str
    duration_ms: float
    result_summary: str
    details: Optional[Dict[str, Any]] = None


class PipelineRunResponse(BaseModel):
    pipeline_id: str
    url: str
    status: str
    total_duration_ms: float
    steps: list[PipelineStep]
    scraped_content: Optional[Dict[str, Any]] = None
    xerebro_analysis: Optional[Dict[str, Any]] = None
    xerebro_available: bool


# Dashboard-compatible models
class DashboardSubmitPipelineRequest(BaseModel):
    url: str = Field(..., description="The URL to scrape")


class DashboardPipelineRunResult(BaseModel):
    id: str
    url: str
    status: str  # 'queued' | 'running' | 'completed' | 'failed'
    extractedData: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    createdAt: str


class DashboardNode(BaseModel):
    name: str
    region: str
    status: str  # 'online' | 'offline'
    cpu: float
    mem: float
    tasks: int


# ── Node protocol models ──

class RegisterNodeRequest(BaseModel):
    hostname: str = Field(..., description="Human-readable node name")
    capabilities: List[str] = Field(default_factory=list, description="Supported task types: scrape, enrich, transform")
    cpu: float = Field(0.0, description="CPU usage percentage")
    ram: float = Field(0.0, description="RAM usage in MB")
    region: str = Field("unknown", description="Geographic region")
    port: int = Field(0, description="Port the node simulator listens on (for result callbacks)")


class NodeInfo(BaseModel):
    id: str
    hostname: str
    capabilities: List[str]
    cpu: float
    ram: float
    region: str
    status: str
    last_heartbeat: str
    task_count: int


class HeartbeatRequest(BaseModel):
    cpu: Optional[float] = None
    ram: Optional[float] = None
    task_count: Optional[int] = None


class DispatchTaskResult(BaseModel):
    task_id: str
    status: str  # 'success' | 'failed'
    scraped_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DashboardPipeline(BaseModel):
    id: str
    name: str
    status: str  # 'running' | 'paused' | 'idle' | 'error'
    nodes: int
    tasks: int
    uptime: str


# ============================================================================
# Engine Lifecycle
# ============================================================================


@app.on_event("startup")
async def startup():
    """Auto-start the engine on API boot."""
    if not WRAITH_ENGINE.is_running():
        WRAITH_ENGINE.start()
        logger.info("WraithEngine auto-started")

    # Check Xerebro/Ollama availability
    xerebro_ok = XEREBRO_BRAIN.check_sync()
    logger.info("Xerebro AI (Ollama) available: %s", xerebro_ok)

    # Start stale-node cleanup loop
    asyncio.create_task(_stale_node_cleanup_loop())
    logger.info("Node heartbeat monitor started (timeout: %ds)", HEARTBEAT_TIMEOUT)


@app.on_event("shutdown")
async def shutdown():
    """Gracefully stop the engine on API shutdown."""
    if WRAITH_ENGINE.is_running():
        WRAITH_ENGINE.stop()
        logger.info("WraithEngine stopped")


# ============================================================================
# Routes — System
# ============================================================================


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "engine": "running" if WRAITH_ENGINE.is_running() else "stopped",
        "xerebro": XEREBRO_BRAIN.is_available,
        "version": "0.1.0",
    }


# ============================================================================
# Routes — Engine
# ============================================================================


@app.get("/api/v1/status", response_model=StatusResponse, tags=["engine"])
async def get_engine_status():
    """Get engine status and resource statistics."""
    return StatusResponse(
        engine="WraithEngine",
        version="0.1.0",
        running=WRAITH_ENGINE.is_running(),
        stats=WRAITH_ENGINE.get_stats(),
    )


@app.post("/api/v1/engine/start", tags=["engine"])
async def start_engine():
    """Start the WraithEngine."""
    if WRAITH_ENGINE.is_running():
        raise HTTPException(status_code=409, detail="Engine already running")
    WRAITH_ENGINE.start()
    return {"message": "Engine started", "status": "running"}


@app.post("/api/v1/engine/stop", tags=["engine"])
async def stop_engine():
    """Stop the WraithEngine."""
    if not WRAITH_ENGINE.is_running():
        raise HTTPException(status_code=409, detail="Engine not running")
    WRAITH_ENGINE.stop()
    return {"message": "Engine stopped", "status": "stopped"}


# ============================================================================
# Routes — Tasks
# ============================================================================


@app.post("/api/v1/tasks", response_model=TaskResponse, tags=["tasks"])
async def create_task(task: TaskRequest, background_tasks: BackgroundTasks):
    """Submit a new task to the engine for processing."""
    if not WRAITH_ENGINE.is_running():
        raise HTTPException(status_code=503, detail="Engine not running")

    config = TaskConfig(
        type=task.type,
        target=task.target,
        payload=task.payload,
        priority=task.priority,
        max_retries=task.max_retries,
        timeout_seconds=task.timeout_seconds,
    )
    WRAITH_ENGINE.submit_task(config)
    task_id = config.id

    return TaskResponse(
        task_id=task_id,
        status="queued",
        message=f"Task {task_id} submitted successfully",
    )


@app.get("/api/v1/tasks/{task_id}", tags=["tasks"])
async def get_task_status(task_id: str):
    """Get the status of a submitted task."""
    return {
        "task_id": task_id,
        "status": "pending",
        "result": None,
    }


# ============================================================================
# Routes — WebSocket (live pipeline events)
# ============================================================================


@app.websocket("/ws/pipelines")
async def websocket_pipelines(ws: WebSocket):
    """WebSocket endpoint for live pipeline events.

    On connect, sends a welcome status event.
    Pipeline run events are broadcast to all connected clients.
    """
    await ws_manager.connect(ws)
    try:
        # Keep connection alive — receive and ignore client pings
        while True:
            data = await ws.receive_text()
            # Clients may send {"type": "ping"} — respond with pong
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
        ws_manager.disconnect(ws)


# ============================================================================
# Routes — Dashboard-Compatible Pipelines API
# ============================================================================


async def _run_pipeline_internal(url: str, pipeline_id: str, dispatch_timeout: float = 30.0) -> Dict[str, Any]:
    """
    Internal pipeline execution — runs the scrape + analysis steps
    and broadcasts events over WebSocket.

    If online worker nodes are available, the scrape step is dispatched
    to a round-robin selected node. Otherwise falls back to local execution.
    """
    steps: list[Dict[str, Any]] = []
    overall_start = time.time()

    # ------------------------------------------------------------------
    # Step 1: Scrape (local or dispatched)
    # ------------------------------------------------------------------
    step1_start = time.time()
    logger.info("Pipeline %s: scraping URL %s", pipeline_id, url)

    if not WRAITH_ENGINE.is_running():
        WRAITH_ENGINE.start()

    # Check for available worker nodes for distributed dispatch
    node = _round_robin_node()
    scrape_result = None

    if node:
        # ── Dispatch to worker node ──
        node_id = node["hostname"]
        dispatch_task_id = str(uuid.uuid4())

        logger.info("Pipeline %s: dispatching scrape to node '%s' (task %s)", pipeline_id, node_id, dispatch_task_id)

        await ws_manager.broadcast_pipeline_event(
            "task_update", pipeline_id,
            {"step": "scrape", "status": "dispatched", "url": url, "node": node_id},
        )

        # Create dispatch task with an asyncio.Event for synchronization
        result_event = asyncio.Event()
        pending_dispatch[dispatch_task_id] = {
            "url": url,
            "node_id": node_id,
            "status": "assigned",
            "result": None,
            "event": result_event,
            "pipeline_id": pipeline_id,
        }

        # Increment node task count
        node["task_count"] = node.get("task_count", 0) + 1

        # Wait for node to complete (with timeout)
        try:
            await asyncio.wait_for(result_event.wait(), timeout=dispatch_timeout)
        except asyncio.TimeoutError:
            logger.warning("Pipeline %s: dispatch to node '%s' timed out after %.0fs", pipeline_id, node_id, dispatch_timeout)
            # Fall through — scrape_result stays None, we report failure
        else:
            task_data = pending_dispatch.pop(dispatch_task_id, None)
            if task_data and task_data.get("result"):
                node_result = task_data["result"]
                if node_result.get("status") == "success" and node_result.get("scraped_data"):
                    # Wrap node result to match WraithEngine scrape result shape
                    node_data = node_result["scraped_data"]
                    # Build a mock TaskResult-like object
                    class NodeScrapeResult:
                        success = True
                        data = json.dumps(node_data)
                        error_message = None
                    scrape_result = NodeScrapeResult()
                    logger.info("Pipeline %s: node '%s' scrape succeeded", pipeline_id, node_id)

        # Cleanup if still present (timeout or error)
        pending_dispatch.pop(dispatch_task_id, None)

    # Fall back to local execution if no nodes available or dispatch failed
    if scrape_result is None and not node:
        logger.info("Pipeline %s: no nodes available, scraping locally", pipeline_id)
        await ws_manager.broadcast_pipeline_event(
            "task_update", pipeline_id,
            {"step": "scrape", "status": "running", "url": url, "node": "local"},
        )
        scrape_result = WRAITH_ENGINE.scrape(url, timeout_seconds=30)
    elif scrape_result is None and node:
        # Dispatch was attempted but failed — log and fall back to local
        logger.info("Pipeline %s: node dispatch failed, falling back to local scrape", pipeline_id)
        await ws_manager.broadcast_pipeline_event(
            "task_update", pipeline_id,
            {"step": "scrape", "status": "running", "url": url, "node": "local-fallback"},
        )
        scrape_result = WRAITH_ENGINE.scrape(url, timeout_seconds=30)

    step1_duration = (time.time() - step1_start) * 1000

    if not scrape_result.success:
        error_msg = scrape_result.error_message or "Scrape failed"
        steps.append({
            "step": "scrape",
            "status": "failed",
            "duration_ms": round(step1_duration, 1),
            "result_summary": error_msg,
        })
        await ws_manager.broadcast_pipeline_event(
            "error", pipeline_id,
            {"step": "scrape", "error": error_msg},
        )
        return {
            "pipeline_id": pipeline_id,
            "url": url,
            "status": "failed",
            "total_duration_ms": round((time.time() - overall_start) * 1000, 1),
            "steps": steps,
            "scraped_content": None,
            "xerebro_analysis": None,
            "xerebro_available": XEREBRO_BRAIN.is_available,
            "error": error_msg,
        }

    # Parse scraped data
    try:
        scraped_data = json.loads(scrape_result.data)
    except json.JSONDecodeError:
        scraped_data = {"raw": scrape_result.data}

    body_len = len(scraped_data.get("body_text", ""))
    title = scraped_data.get("title", "")

    steps.append({
        "step": "scrape",
        "status": "success",
        "duration_ms": round(step1_duration, 1),
        "result_summary": f"body: {body_len} chars | status: {scraped_data.get('status_code', '?')}",
        "details": {
            "url": url,
            "status_code": scraped_data.get("status_code"),
            "content_type": scraped_data.get("content_type"),
            "title": title,
            "body_length": body_len,
        },
    })

    await ws_manager.broadcast_pipeline_event(
        "task_update", pipeline_id,
        {"step": "scrape", "status": "success", "title": title, "body_length": body_len},
    )

    # ------------------------------------------------------------------
    # Step 2: Xerebro AI analysis
    # ------------------------------------------------------------------
    xerebro_analysis = None
    xerebro_available = XEREBRO_BRAIN.is_available
    error = None

    if xerebro_available:
        step2_start = time.time()

        prompt = (
            "Analyze the following web page content. Extract the main topic, "
            "key entities (people, organizations, products), and provide a "
            "one-paragraph summary."
        )

        context = {
            "url": url,
            "title": title,
            "body_text": scraped_data.get("body_text", "")[:10000],
            "status_code": scraped_data.get("status_code"),
        }

        await ws_manager.broadcast_pipeline_event(
            "reasoning", pipeline_id,
            {"step": "xerebro_analysis", "status": "running"},
        )

        xerebro_result = XEREBRO_BRAIN.reason_sync(
            prompt=prompt,
            context=context,
            temperature=0.1,
            max_tokens=1024,
            format="json",
        )

        step2_duration = (time.time() - step2_start) * 1000

        if xerebro_result.success:
            try:
                xerebro_analysis = json.loads(xerebro_result.content)
            except (json.JSONDecodeError, TypeError):
                xerebro_analysis = {"raw_response": xerebro_result.content}

            steps.append({
                "step": "xerebro_analysis",
                "status": "success",
                "duration_ms": round(step2_duration, 1),
                "result_summary": f"Tokens: {xerebro_result.tokens_used} | Model: {xerebro_result.model}",
                "details": {
                    "model": xerebro_result.model,
                    "tokens_used": xerebro_result.tokens_used,
                },
            })

            await ws_manager.broadcast_pipeline_event(
                "result", pipeline_id,
                {"step": "xerebro_analysis", "status": "success",
                 "analysis": xerebro_analysis},
            )
        else:
            error = xerebro_result.error or "Xerebro analysis failed"
            steps.append({
                "step": "xerebro_analysis",
                "status": "failed",
                "duration_ms": round(step2_duration, 1),
                "result_summary": error,
            })
            xerebro_available = False
    else:
        steps.append({
            "step": "xerebro_analysis",
            "status": "skipped",
            "duration_ms": 0.0,
            "result_summary": "Ollama not available — install ollama and run `ollama pull llama3.2`",
        })

    total_duration = (time.time() - overall_start) * 1000

    result = {
        "pipeline_id": pipeline_id,
        "url": url,
        "status": "success" if not error else "partial",
        "total_duration_ms": round(total_duration, 1),
        "steps": steps,
        "scraped_content": {
            "title": title,
            "body_text": scraped_data.get("body_text", "")[:500],
            "status_code": scraped_data.get("status_code"),
            "content_type": scraped_data.get("content_type"),
        },
        "xerebro_analysis": xerebro_analysis,
        "xerebro_available": xerebro_available,
    }

    # Store result
    pipeline_data = result.copy()
    pipeline_data["url"] = url
    _store_pipeline(pipeline_id, pipeline_data)

    return result


# ── Dashboard-compatible POST /api/pipelines ──


@app.post("/api/pipelines", tags=["dashboard"])
async def dashboard_submit_pipeline(req: DashboardSubmitPipelineRequest, background_tasks: BackgroundTasks):
    """Submit a pipeline for URL scraping + analysis (dashboard-compatible).

    The dashboard sends just `{"url": "..."}` and expects a quick response
    with the pipeline ID and status. Execution happens in the background.
    """
    if not WRAITH_ENGINE.is_running():
        raise HTTPException(status_code=503, detail="Engine not running")

    pipeline_id = str(uuid.uuid4())

    # Store as queued initially
    _store_pipeline(pipeline_id, {
        "id": pipeline_id,
        "url": req.url,
        "status": "queued",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })

    # Kick off pipeline execution in the background
    async def _run_and_store():
        try:
            result = await _run_pipeline_internal(req.url, pipeline_id)
            _update_pipeline(pipeline_id, {
                "status": "completed" if result.get("status") == "success" else "failed",
                "result": result,
            })
        except Exception as e:
            logger.error("Pipeline %s background task failed: %s", pipeline_id, e)
            _update_pipeline(pipeline_id, {
                "status": "failed",
                "result": {"error": str(e)},
            })

    asyncio.create_task(_run_and_store())

    return {
        "id": pipeline_id,
        "url": req.url,
        "status": "queued",
        "extractedData": None,
        "error": None,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


# ── Dashboard-compatible GET /api/pipelines ──


@app.get("/api/pipelines", tags=["dashboard"])
async def dashboard_list_pipelines():
    """List all pipeline runs."""
    pipelines = []
    for pid, data in pipeline_store.items():
        pipelines.append({
            "id": pid,
            "name": f"Pipeline {pid[:8]}",
            "status": data.get("status", "idle") if data.get("status") != "completed" else "idle",
            "nodes": 1,
            "tasks": len(data.get("result", {}).get("steps", [])),
            "uptime": "0s",
        })
    return pipelines


# ── Dashboard-compatible GET /api/pipelines/{id} ──


@app.get("/api/pipelines/{pipeline_id}", tags=["dashboard"])
async def dashboard_get_pipeline_status(pipeline_id: str):
    """Get the status of a pipeline run."""
    data = pipeline_store.get(pipeline_id)
    if not data:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    result = data.get("result", {})
    status = data.get("status", "queued")
    error = result.get("error") if isinstance(result, dict) else None

    return {
        "id": pipeline_id,
        "url": data.get("url", ""),
        "status": status if status != "completed" else "completed",
        "extractedData": result.get("scraped_content") if isinstance(result, dict) else None,
        "error": error,
        "createdAt": data.get("created_at", ""),
    }


# ── Dashboard-compatible POST /api/pipelines/{id}/pause & resume ──


@app.post("/api/pipelines/{pipeline_id}/pause", tags=["dashboard"])
async def dashboard_pause_pipeline(pipeline_id: str):
    """Pause a running pipeline."""
    data = pipeline_store.get(pipeline_id)
    if not data:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    _update_pipeline(pipeline_id, {"status": "paused"})
    return {"message": f"Pipeline {pipeline_id} paused"}


@app.post("/api/pipelines/{pipeline_id}/resume", tags=["dashboard"])
async def dashboard_resume_pipeline(pipeline_id: str):
    """Resume a paused pipeline."""
    data = pipeline_store.get(pipeline_id)
    if not data:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    _update_pipeline(pipeline_id, {"status": "running"})
    return {"message": f"Pipeline {pipeline_id} resumed"}


# ── Dashboard-compatible GET /api/nodes ──


@app.get("/api/nodes", tags=["dashboard"])
async def dashboard_list_nodes():
    """List all registered compute nodes from the live registry."""
    nodes = []
    for nid, node in node_registry.items():
        nodes.append(DashboardNode(
            name=nid,
            region=node.get("region", "unknown"),
            status=node.get("status", "offline"),
            cpu=node.get("cpu", 0.0),
            mem=node.get("ram", 0.0),
            tasks=node.get("task_count", 0),
        ))
    # If no live nodes registered, return empty list (caller handles empty state)
    return nodes


@app.get("/api/nodes/{name}", tags=["dashboard"])
async def dashboard_get_node(name: str):
    """Get details for a specific compute node."""
    node = node_registry.get(name)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{name}' not found")
    return DashboardNode(
        name=name,
        region=node.get("region", "unknown"),
        status=node.get("status", "offline"),
        cpu=node.get("cpu", 0.0),
        mem=node.get("ram", 0.0),
        tasks=node.get("task_count", 0),
    )


# ============================================================================
# Routes — Distributed Node Protocol
# ============================================================================


@app.post("/api/v1/nodes/register", tags=["nodes"])
async def register_node(req: RegisterNodeRequest):
    """Register a new compute node or re-register an existing one.

    Called by worker nodes on startup. Returns a unique node ID.
    If the hostname is already registered, update the registration.
    """
    # Use hostname as node ID for simplicity (can be made more robust with UUID)
    node_id = req.hostname

    existing = node_registry.get(node_id)
    is_new = existing is None

    node_registry[node_id] = {
        "hostname": req.hostname,
        "capabilities": req.capabilities,
        "cpu": req.cpu,
        "ram": req.ram,
        "region": req.region,
        "port": req.port,
        "status": "online",
        "last_heartbeat": time.time(),
        "task_count": existing.get("task_count", 0) if existing else 0,
        "registered_at": existing.get("registered_at", datetime.now(timezone.utc).isoformat()) if existing else datetime.now(timezone.utc).isoformat(),
    }

    action = "registered" if is_new else "re-registered"
    logger.info("Node '%s' %s (capabilities=%s, region=%s)", node_id, action, req.capabilities, req.region)

    await ws_manager.broadcast_pipeline_event(
        "status", "",
        {"event": f"node_{action}", "node_id": node_id, "hostname": req.hostname},
    )

    return {
        "node_id": node_id,
        "status": "online",
        "message": f"Node '{node_id}' {action} successfully",
    }


@app.post("/api/v1/nodes/{node_id}/heartbeat", tags=["nodes"])
async def node_heartbeat(node_id: str, hb: HeartbeatRequest = HeartbeatRequest()):
    """Receive a heartbeat ping from a registered node.

    Updates CPU/RAM/task count and refreshes the liveness timestamp.
    Nodes should call this every ~10 seconds.
    """
    node = node_registry.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not registered. Call /register first.")

    node["last_heartbeat"] = time.time()
    node["status"] = "online"

    if hb.cpu is not None:
        node["cpu"] = hb.cpu
    if hb.ram is not None:
        node["ram"] = hb.ram
    if hb.task_count is not None:
        node["task_count"] = hb.task_count

    return {"node_id": node_id, "status": "online", "ack": True}


@app.get("/api/v1/nodes", tags=["nodes"])
async def list_nodes_v1():
    """List all registered nodes with full metadata (v1 API)."""
    nodes = []
    for nid, node in node_registry.items():
        last_hb = node.get("last_heartbeat", 0)
        nodes.append(NodeInfo(
            id=nid,
            hostname=node.get("hostname", nid),
            capabilities=node.get("capabilities", []),
            cpu=node.get("cpu", 0.0),
            ram=node.get("ram", 0.0),
            region=node.get("region", "unknown"),
            status=node.get("status", "offline"),
            last_heartbeat=datetime.fromtimestamp(last_hb, tz=timezone.utc).isoformat() if last_hb else "never",
            task_count=node.get("task_count", 0),
        ))
    return {"nodes": nodes, "count": len(nodes), "online": len(_get_online_nodes())}


@app.get("/api/v1/nodes/{node_id}/tasks", tags=["nodes"])
async def node_poll_tasks(node_id: str):
    """Poll for pending tasks assigned to this node.

    Worker nodes call this to check for new dispatch work.
    """
    node = node_registry.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found. Register first.")

    # Find pending tasks assigned to this node
    tasks = []
    for tid, task in list(pending_dispatch.items()):
        if task.get("node_id") == node_id and task.get("status") == "assigned":
            tasks.append({
                "task_id": tid,
                "url": task.get("url"),
                "status": "assigned",
            })

    return {"node_id": node_id, "tasks": tasks, "count": len(tasks)}


@app.post("/api/v1/nodes/{node_id}/tasks/{task_id}/result", tags=["nodes"])
async def node_submit_task_result(node_id: str, task_id: str, result: DispatchTaskResult):
    """Worker node submits the result of a dispatched task."""
    task = pending_dispatch.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found in dispatch queue")

    if task.get("node_id") != node_id:
        raise HTTPException(status_code=403, detail=f"Task '{task_id}' was assigned to node '{task['node_id']}', not '{node_id}'")

    task["status"] = result.status
    task["result"] = result.model_dump()

    # Signal the waiting pipeline that the result is ready
    event = task.get("event")
    if event:
        event.set()

    # Update node task count
    node = node_registry.get(node_id)
    if node:
        node["task_count"] = max(0, node.get("task_count", 0) - 1)

    logger.info("Node %s completed task %s: %s", node_id, task_id, result.status)
    return {"ack": True, "task_id": task_id, "status": result.status}


# ============================================================================
# Routes — Nectar Marketplace
# ============================================================================

# In-memory marketplace store
MARKETPLACE_MODULES = [
    {
        "id": "mod-ecom-price-mon",
        "name": "E-commerce Price Monitor",
        "description": "Track competitor pricing across Amazon, Walmart, Shopify and 20+ retailers. Get alerts on price drops and MAP violations.",
        "author": "Supra-Codex",
        "rating": 4.8,
        "downloads": 1240,
        "price": 0,
        "price_label": "Free",
        "category": "Scraping",
        "version": "1.2.0",
        "install_count": 1240,
        "features": ["Multi-retailer scraping", "Price history tracking", "MAP violation alerts", "CSV/API export"],
        "requirements": ["WraithEngine >= 0.1.0", "Python >= 3.9"],
    },
    {
        "id": "mod-lead-gen-pro",
        "name": "Lead Gen Prospector",
        "description": "Extract and enrich B2B leads from LinkedIn, Crunchbase, and AngelList. Includes company enrichment and contact finding.",
        "author": "DataFlow Labs",
        "rating": 4.6,
        "downloads": 873,
        "price": 29,
        "price_label": "$29",
        "category": "Leads",
        "version": "2.0.1",
        "install_count": 873,
        "features": ["LinkedIn profile extraction", "Company enrichment", "Contact email finder", "CRM export"],
        "requirements": ["WraithEngine >= 0.1.0", "Xerebro AI >= 0.1.0"],
    },
    {
        "id": "mod-competitive-intel",
        "name": "Competitive Intel Scanner",
        "description": "Monitor competitor websites, pricing pages, job postings, and product launches. Get weekly digests of competitive moves.",
        "author": "IntelStack",
        "rating": 4.5,
        "downloads": 654,
        "price": 19,
        "price_label": "$19",
        "category": "Analysis",
        "version": "1.5.0",
        "install_count": 654,
        "features": ["Website change detection", "Job posting monitoring", "Product launch alerts", "Weekly digests"],
        "requirements": ["WraithEngine >= 0.1.0"],
    },
    {
        "id": "mod-social-sentiment",
        "name": "Social Sentiment Analyzer",
        "description": "Analyze social media sentiment for brands, products, or trends. Supports Twitter/X, Reddit, and news sources with AI-powered classification.",
        "author": "TrendViz",
        "rating": 4.3,
        "downloads": 421,
        "price": 39,
        "price_label": "$39",
        "category": "Analysis",
        "version": "1.0.0",
        "install_count": 421,
        "features": ["Multi-platform monitoring", "AI sentiment classification", "Trend detection", "Dashboard widgets"],
        "requirements": ["WraithEngine >= 0.1.0", "Xerebro AI >= 0.1.0"],
    },
]

# In-memory installed modules store
INSTALLED_MODULES: Dict[str, List[str]] = {
    "default": ["mod-ecom-price-mon"],
}


class MarketplaceModuleOut(BaseModel):
    id: str
    name: str
    description: str
    author: str
    rating: float
    downloads: int
    price: int
    price_label: str
    category: str
    version: str
    install_count: int
    features: list[str]
    requirements: list[str]
    installed: bool = False


@app.get("/api/marketplace/modules", tags=["marketplace"])
async def marketplace_list_modules():
    """List all modules available in the Nectar Marketplace."""
    installed = INSTALLED_MODULES.get("default", [])
    modules = []
    for mod in MARKETPLACE_MODULES:
        modules.append(MarketplaceModuleOut(
            **{k: v for k, v in mod.items() if k != "installed"},
            installed=mod["id"] in installed,
        ))
    return modules


@app.get("/api/marketplace/modules/{module_id}", tags=["marketplace"])
async def marketplace_get_module(module_id: str):
    """Get detailed information about a specific marketplace module."""
    for mod in MARKETPLACE_MODULES:
        if mod["id"] == module_id:
            installed = INSTALLED_MODULES.get("default", [])
            return MarketplaceModuleOut(
                **{k: v for k, v in mod.items() if k != "installed"},
                installed=module_id in installed,
            )
    raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")


class InstallRequest(BaseModel):
    module_id: str


@app.post("/api/marketplace/modules/{module_id}/install", tags=["marketplace"])
async def marketplace_install_module(module_id: str):
    """Install a module from the marketplace."""
    # Verify module exists
    found = None
    for mod in MARKETPLACE_MODULES:
        if mod["id"] == module_id:
            found = mod
            break
    if not found:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")

    # Add to installed
    if "default" not in INSTALLED_MODULES:
        INSTALLED_MODULES["default"] = []
    if module_id not in INSTALLED_MODULES["default"]:
        INSTALLED_MODULES["default"].append(module_id)
        # Increment install count
        found["install_count"] += 1
        found["downloads"] += 1

    return {"message": f"Module '{found['name']}' installed successfully", "module_id": module_id}


@app.post("/api/marketplace/modules/{module_id}/uninstall", tags=["marketplace"])
async def marketplace_uninstall_module(module_id: str):
    """Uninstall a module."""
    installed = INSTALLED_MODULES.get("default", [])
    if module_id in installed:
        INSTALLED_MODULES["default"] = [m for m in installed if m != module_id]
    return {"message": "Module uninstalled", "module_id": module_id}


@app.get("/api/marketplace/installed", tags=["marketplace"])
async def marketplace_list_installed():
    """List all installed modules with full details."""
    installed_ids = INSTALLED_MODULES.get("default", [])
    modules = []
    for mod in MARKETPLACE_MODULES:
        if mod["id"] in installed_ids:
            modules.append(MarketplaceModuleOut(
                **{k: v for k, v in mod.items() if k != "installed"},
                installed=True,
            ))
    return modules


# ============================================================================
# Routes — /api/v1/ Pipelines (versioned, full config)
# ============================================================================


@app.get("/api/v1/pipelines/{pipeline_id}", tags=["pipelines"])
async def get_pipeline_by_id(pipeline_id: str):
    """Get a saved pipeline definition, or fall back to a pipeline run result."""
    # Prefer a saved pipeline definition if present
    definition = pipeline_definitions.get(pipeline_id)
    if definition:
        return definition
    data = pipeline_store.get(pipeline_id)
    if not data:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return data


@app.post(
    "/api/v1/pipelines/run",
    response_model=PipelineRunResponse,
    tags=["pipelines"],
    summary="Run an end-to-end URL scraping pipeline",
)
async def run_pipeline_v1(req: PipelineRunRequest):
    """
    End-to-end pipeline: URL → Scrape → Xerebro AI Enrich → Result.

    Accepts full configuration (custom prompt, model override).
    """
    pipeline_id = str(uuid.uuid4())
    steps: list[Dict[str, Any]] = []
    overall_start = time.time()

    # ------------------------------------------------------------------
    # Step 1: Scrape
    # ------------------------------------------------------------------
    step1_start = time.time()
    logger.info("Pipeline %s: scraping URL %s", pipeline_id, req.url)

    if not WRAITH_ENGINE.is_running():
        WRAITH_ENGINE.start()

    scrape_result = WRAITH_ENGINE.scrape(req.url, timeout_seconds=30)
    step1_duration = (time.time() - step1_start) * 1000

    if not scrape_result.success:
        steps.append(PipelineStep(
            step="scrape",
            status="failed",
            duration_ms=round(step1_duration, 1),
            result_summary=scrape_result.error_message or "Scrape failed",
        ))
        return PipelineRunResponse(
            pipeline_id=pipeline_id,
            url=req.url,
            status="failed",
            total_duration_ms=round((time.time() - overall_start) * 1000, 1),
            steps=steps,
            scraped_content=None,
            xerebro_analysis=None,
            xerebro_available=XEREBRO_BRAIN.is_available,
        )

    try:
        scraped_data = json.loads(scrape_result.data)
    except json.JSONDecodeError:
        scraped_data = {"raw": scrape_result.data}

    body_len = len(scraped_data.get("body_text", ""))
    summary_parts = []
    if scraped_data.get("title"):
        summary_parts.append(f"title: {scraped_data['title'][:80]}")
    summary_parts.append(f"body: {body_len} chars")
    summary_parts.append(f"status: {scraped_data.get('status_code', '?')}")

    steps.append(PipelineStep(
        step="scrape",
        status="success",
        duration_ms=round(step1_duration, 1),
        result_summary=" | ".join(summary_parts),
        details={
            "url": req.url,
            "status_code": scraped_data.get("status_code"),
            "content_type": scraped_data.get("content_type"),
            "title": scraped_data.get("title"),
            "body_length": body_len,
        },
    ))

    # ------------------------------------------------------------------
    # Step 2: Xerebro AI analysis
    # ------------------------------------------------------------------
    xerebro_analysis = None
    xerebro_available = XEREBRO_BRAIN.is_available

    if xerebro_available:
        step2_start = time.time()

        custom_prompt = req.prompt or (
            "Analyze the following web page content. Extract the main topic, "
            "key entities (people, organizations, products), and provide a "
            "one-paragraph summary."
        )

        context = {
            "url": req.url,
            "title": scraped_data.get("title", ""),
            "body_text": scraped_data.get("body_text", "")[:10000],
            "status_code": scraped_data.get("status_code"),
        }

        logger.info(
            "Pipeline %s: Xerebro reasoning with model %s",
            pipeline_id,
            req.xerebro_model or XEREBRO_BRAIN.config.model,
        )

        brain = XEREBRO_BRAIN
        if req.xerebro_model and req.xerebro_model != brain.config.model:
            brain = XerebroBrain(XerebroConfig(model=req.xerebro_model))

        xerebro_result = brain.reason_sync(
            prompt=custom_prompt,
            context=context,
            temperature=0.1,
            max_tokens=1024,
            format="json",
        )

        step2_duration = (time.time() - step2_start) * 1000

        if xerebro_result.success:
            try:
                xerebro_analysis = json.loads(xerebro_result.content)
            except (json.JSONDecodeError, TypeError):
                xerebro_analysis = {"raw_response": xerebro_result.content}

            steps.append(PipelineStep(
                step="xerebro_analysis",
                status="success",
                duration_ms=round(step2_duration, 1),
                result_summary=f"Tokens used: {xerebro_result.tokens_used} | Model: {xerebro_result.model}",
                details={
                    "model": xerebro_result.model,
                    "tokens_used": xerebro_result.tokens_used,
                },
            ))
            xerebro_available = True
        else:
            steps.append(PipelineStep(
                step="xerebro_analysis",
                status="failed",
                duration_ms=round(step2_duration, 1),
                result_summary=xerebro_result.error or "Xerebro analysis failed",
            ))
            xerebro_available = False
    else:
        steps.append(PipelineStep(
            step="xerebro_analysis",
            status="skipped",
            duration_ms=0.0,
            result_summary="Ollama not available — install ollama and run `ollama pull llama3.2`",
        ))

    total_duration = (time.time() - overall_start) * 1000

    result = PipelineRunResponse(
        pipeline_id=pipeline_id,
        url=req.url,
        status="success",
        total_duration_ms=round(total_duration, 1),
        steps=steps,
        scraped_content={
            "title": scraped_data.get("title"),
            "body_text": scraped_data.get("body_text", "")[:500],
            "status_code": scraped_data.get("status_code"),
            "content_type": scraped_data.get("content_type"),
        },
        xerebro_analysis=xerebro_analysis,
        xerebro_available=xerebro_available,
    )

    # Store the result
    _store_pipeline(pipeline_id, {
        "id": pipeline_id,
        "url": req.url,
        "status": "completed",
        "result": result.model_dump(),
    })

    return result


# ============================================================================
# Routes — Xerebro AI Brain Panel (chat + models)
# ============================================================================


class XerebroChatMessage(BaseModel):
    role: str = Field(..., description="user | assistant")
    content: str = Field(..., description="Message content")


class XerebroChatRequest(BaseModel):
    prompt: str = Field(..., description="The latest user message")
    model: Optional[str] = Field(
        None, description="Ollama model to use (defaults to the configured model)"
    )
    system_prompt: Optional[str] = Field(
        None, description="Override the system prompt for this chat"
    )
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(1024, ge=1, le=8192)
    history: List[XerebroChatMessage] = Field(
        default_factory=list, description="Prior conversation turns (user/assistant)"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Optional structured context (e.g. scraped page content)"
    )


class XerebroChatResponse(BaseModel):
    success: bool
    response: str
    model: str
    tokens_used: int
    error: Optional[str] = None


def _build_chat_prompt(req: XerebroChatRequest) -> str:
    """Build a multi-turn chat prompt with optional context."""
    parts = []
    for msg in req.history:
        role = "User" if msg.role == "user" else "Assistant"
        parts.append(f"{role}:\n{msg.content}")
    if req.context:
        parts.append(f"Context:\n{json.dumps(req.context, indent=2, ensure_ascii=False)}")
    parts.append(f"User:\n{req.prompt}")
    return "\n\n".join(parts)


@app.get("/api/v1/xerebro/models", tags=["xerebro"])
async def xerebro_list_models():
    """List the Ollama models available to the local Xerebro brain."""
    import httpx

    try:
        with httpx.Client(base_url=XEREBRO_BRAIN.config.ollama_host, timeout=10) as client:
            resp = client.get("/api/tags")
            if resp.status_code != 200:
                return {
                    "available": False,
                    "models": [],
                    "default_model": XEREBRO_BRAIN.config.model,
                    "error": f"Ollama responded with status {resp.status_code}",
                }
            data = resp.json()
            models = [
                {
                    "name": m.get("name", ""),
                    "size": m.get("size", 0),
                    "modified_at": m.get("modified_at", ""),
                }
                for m in data.get("models", [])
            ]
            return {
                "available": True,
                "models": models,
                "default_model": XEREBRO_BRAIN.config.model,
            }
    except Exception as e:
        logger.warning("Xerebro /models failed: %s", e)
        return {
            "available": False,
            "models": [],
            "default_model": XEREBRO_BRAIN.config.model,
            "error": str(e),
        }


@app.post("/api/v1/xerebro/chat", response_model=XerebroChatResponse, tags=["xerebro"])
async def xerebro_chat(req: XerebroChatRequest):
    """Send a chat message to the local Xerebro AI brain and get a response."""
    if not XEREBRO_BRAIN.check_sync():
        return XerebroChatResponse(
            success=False,
            response="",
            model=req.model or XEREBRO_BRAIN.config.model,
            tokens_used=0,
            error="Ollama is not available. Install Ollama and run `ollama pull llama3.2`.",
        )

    model = req.model or XEREBRO_BRAIN.config.model
    system_prompt = req.system_prompt or XEREBRO_BRAIN.config.system_prompt

    # Use a dedicated brain instance for the requested model + system prompt
    # so per-chat settings never mutate the global brain.
    brain = XerebroBrain(XerebroConfig(model=model, system_prompt=system_prompt))
    chat_prompt = _build_chat_prompt(req)

    result = brain.reason_sync(
        prompt=chat_prompt,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        format="text",
    )

    return XerebroChatResponse(
        success=result.success,
        response=result.content,
        model=result.model,
        tokens_used=result.tokens_used,
        error=result.error,
    )


# ============================================================================
# Routes — Visual Pipeline Builder (saved pipeline definitions)
# ============================================================================

# In-memory store of saved pipeline definitions: id → PipelineDefinition
pipeline_definitions: Dict[str, Dict[str, Any]] = {}


class PipelineStepDef(BaseModel):
    """A single step in a saved pipeline definition."""

    id: str
    type: str = Field(..., description="scrape | enrich | filter | transform | export")
    name: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)


class PipelineDefinitionModel(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., description="Pipeline name")
    description: str = Field("", description="Pipeline description")
    steps: List[PipelineStepDef] = Field(default_factory=list)


class PipelineRunStepResult(BaseModel):
    step_id: str
    type: str
    status: str  # success | failed | skipped
    output: Optional[Any] = None
    summary: Optional[str] = None
    error: Optional[str] = None


class PipelineRunOut(BaseModel):
    id: str
    name: str
    status: str
    duration_ms: float
    steps: List[PipelineRunStepResult]
    result: Optional[Any] = None


@app.post("/api/v1/pipelines", tags=["pipelines"])
async def save_pipeline_definition(pipeline: PipelineDefinitionModel):
    """Create a new pipeline definition or save an existing one (by id)."""
    if not pipeline.steps:
        raise HTTPException(status_code=400, detail="Pipeline must contain at least one step")

    pid = pipeline.id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    existing = pipeline_definitions.get(pid)
    pipeline_definitions[pid] = {
        "id": pid,
        "name": pipeline.name,
        "description": pipeline.description,
        "steps": [s.model_dump() for s in pipeline.steps],
        "created_at": existing.get("created_at", now) if existing else now,
        "updated_at": now,
    }
    return {"id": pid, "message": f"Pipeline '{pipeline.name}' saved", "pipeline": pipeline_definitions[pid]}


@app.get("/api/v1/pipelines", tags=["pipelines"])
async def list_pipeline_definitions():
    """List all saved pipeline definitions."""
    pipes = []
    for pid, data in pipeline_definitions.items():
        pipes.append({
            "id": pid,
            "name": data.get("name", pid),
            "description": data.get("description", ""),
            "steps": len(data.get("steps", [])),
            "types": sorted(set(s.get("type") for s in data.get("steps", []))),
            "updated_at": data.get("updated_at", ""),
        })
    # Sort by most recently updated first
    pipes.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return pipes


@app.delete("/api/v1/pipelines/{pipeline_id}", tags=["pipelines"])
async def delete_pipeline_definition(pipeline_id: str):
    """Delete a saved pipeline definition."""
    if pipeline_id not in pipeline_definitions:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    name = pipeline_definitions[pipeline_id]["name"]
    del pipeline_definitions[pipeline_id]
    return {"message": f"Pipeline '{name}' deleted", "id": pipeline_id}


def _execute_step(step: PipelineStepDef, data: Dict[str, Any]) -> PipelineRunStepResult:
    """Execute a single pipeline step against the working dataset."""
    stype = step.type
    cfg = step.config or {}
    summary = ""

    if stype == "scrape":
        url = cfg.get("url", data.get("url", ""))
        if not url:
            return PipelineRunStepResult(
                step_id=step.id, type=stype, status="failed",
                output=None, error="Scrape step requires a url",
            )
        if not WRAITH_ENGINE.is_running():
            WRAITH_ENGINE.start()
        result = WRAITH_ENGINE.scrape(url, timeout_seconds=30)
        if not result.success:
            return PipelineRunStepResult(
                step_id=step.id, type=stype, status="failed",
                output=None, error=result.error_message or "Scrape failed",
            )
        try:
            scraped = json.loads(result.data)
        except json.JSONDecodeError:
            scraped = {"raw": result.data}
        body = scraped.get("body_text", "")
        data["url"] = url
        data["title"] = scraped.get("title", "")
        data["body_text"] = body
        data["status_code"] = scraped.get("status_code")
        summary = f"body: {len(body)} chars | title: {data['title'][:60] if data['title'] else '—'}"
        return PipelineRunStepResult(
            step_id=step.id, type=stype, status="success",
            output={"title": data["title"], "body_length": len(body), "status_code": data.get("status_code")},
            summary=summary,
        )

    if stype == "enrich":
        prompt = cfg.get("prompt", "")
        if not XEREBRO_BRAIN.is_available:
            return PipelineRunStepResult(
                step_id=step.id, type=stype, status="skipped",
                output=None, summary="Ollama not available — enrichment skipped",
            )
        model = cfg.get("model") or XEREBRO_BRAIN.config.model
        brain = XerebroBrain(XerebroConfig(model=model)) if model != XEREBRO_BRAIN.config.model else XEREBRO_BRAIN
        context = {
            "title": data.get("title", ""),
            "body_text": (data.get("body_text", "") or "")[:10000],
            "url": data.get("url", ""),
        }
        result = brain.reason_sync(
            prompt=prompt or "Extract the main topic, entities, and a concise summary of this page.",
            context=context,
            temperature=cfg.get("temperature", 0.1),
            max_tokens=cfg.get("max_tokens", 1024),
            format="json",
        )
        if not result.success:
            return PipelineRunStepResult(
                step_id=step.id, type=stype, status="failed",
                output=None, error=result.error or "Enrichment failed",
            )
        try:
            parsed = json.loads(result.content)
        except (json.JSONDecodeError, TypeError):
            parsed = {"raw_response": result.content}
        data["enrichment"] = parsed
        data["tokens_used"] = data.get("tokens_used", 0) + result.tokens_used
        summary = f"tokens: {result.tokens_used} | model: {result.model}"
        return PipelineRunStepResult(
            step_id=step.id, type=stype, status="success",
            output=parsed, summary=summary,
        )

    if stype == "filter":
        # Simple include/field filter on the text; passthrough by default.
        field = cfg.get("field", "")
        contains = cfg.get("contains", "")
        text = ""
        if field and field in data:
            text = str(data[field])
        elif field == "body_text":
            text = str(data.get("body_text", ""))
        else:
            text = json.dumps({k: v for k, v in data.items() if k != "body_text"})
        kept = (not contains) or (contains.lower() in text.lower())
        summary = f"kept={kept} (contains '{contains}')" if contains else "passthrough (no filter)"
        return PipelineRunStepResult(
            step_id=step.id, type=stype, status="success",
            output={"kept": kept, "matched": kept, "filter": contains},
            summary=summary,
        )

    if stype == "transform":
        fmt = cfg.get("format", "json")
        field = cfg.get("field", "")
        value = data.get(field) if field else data
        summary = f"format: {fmt}, field: {field or 'all'}"
        return PipelineRunStepResult(
            step_id=step.id, type=stype, status="success",
            output=value, summary=summary,
        )

    if stype == "export":
        fmt = cfg.get("format", "json")
        try:
            payload = json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            payload = str(data)
        summary = f"{fmt.upper()} export ({len(payload)} bytes)"
        return PipelineRunStepResult(
            step_id=step.id, type=stype, status="success",
            output=payload, summary=summary,
        )

    return PipelineRunStepResult(
        step_id=step.id, type=stype, status="skipped",
        output=None, error=f"Unknown step type '{stype}'",
    )


@app.post("/api/v1/pipelines/{pipeline_id}/run", tags=["pipelines"])
async def run_pipeline_definition(pipeline_id: str):
    """Execute a saved pipeline definition end-to-end."""
    definition = pipeline_definitions.get(pipeline_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Pipeline definition not found")

    overall_start = time.time()
    data: Dict[str, Any] = {"url": ""}
    step_results: List[PipelineRunStepResult] = []

    for step_dict in definition.get("steps", []):
        step = PipelineStepDef(**step_dict)
        result = _execute_step(step, data)
        step_results.append(result)
        logger.info("Pipeline def %s step %s (%s): %s", pipeline_id, step.id, step.type, result.status)

    total_duration = (time.time() - overall_start) * 1000
    # Final result — export payload if present, else the working dataset summary
    final_output = data

    return PipelineRunOut(
        id=pipeline_id,
        name=definition.get("name", pipeline_id),
        status="success",
        duration_ms=round(total_duration, 1),
        steps=step_results,
        result=final_output,
    )


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )