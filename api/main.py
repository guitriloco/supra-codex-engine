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


async def _run_pipeline_internal(url: str, pipeline_id: str) -> Dict[str, Any]:
    """
    Internal pipeline execution — runs the scrape + analysis steps
    and broadcasts events over WebSocket.
    """
    steps: list[Dict[str, Any]] = []
    overall_start = time.time()

    # ------------------------------------------------------------------
    # Step 1: Scrape
    # ------------------------------------------------------------------
    step1_start = time.time()
    logger.info("Pipeline %s: scraping URL %s", pipeline_id, url)

    if not WRAITH_ENGINE.is_running():
        WRAITH_ENGINE.start()

    await ws_manager.broadcast_pipeline_event(
        "task_update", pipeline_id,
        {"step": "scrape", "status": "running", "url": url},
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
    """List all registered compute nodes (mock data for now)."""
    return [
        DashboardNode(name="node-alpha-01", region="us-east", status="online",
                      cpu=23.4, mem=45.2, tasks=3),
        DashboardNode(name="node-beta-02", region="eu-west", status="online",
                      cpu=12.1, mem=31.8, tasks=1),
        DashboardNode(name="node-gamma-03", region="ap-southeast", status="offline",
                      cpu=0.0, mem=0.0, tasks=0),
    ]


@app.get("/api/nodes/{name}", tags=["dashboard"])
async def dashboard_get_node(name: str):
    """Get details for a specific compute node."""
    nodes = await dashboard_list_nodes()
    for node in nodes:
        if node.name == name:
            return node
    raise HTTPException(status_code=404, detail=f"Node '{name}' not found")


# ============================================================================
# Routes — /api/v1/ Pipelines (versioned, full config)
# ============================================================================


@app.get("/api/v1/pipelines/{pipeline_id}", tags=["pipelines"])
async def get_pipeline_by_id(pipeline_id: str):
    """Get the full result of a pipeline run."""
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