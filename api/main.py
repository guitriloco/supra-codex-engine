"""
Supra-Codex Engine — REST API Server

FastAPI-based REST API that exposes the WraithEngine capabilities
to the orchestration dashboard and external clients.
"""

import json
import logging
import os
import uuid
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
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
    future = WRAITH_ENGINE.submit_task(config)
    task_id = config.id

    return TaskResponse(
        task_id=task_id,
        status="queued",
        message=f"Task {task_id} submitted successfully",
    )


@app.get("/api/v1/tasks/{task_id}", tags=["tasks"])
async def get_task_status(task_id: str):
    """Get the status of a submitted task."""
    # TODO: Implement task status tracking with in-memory store
    return {
        "task_id": task_id,
        "status": "pending",
        "result": None,
    }


# ============================================================================
# Routes — Pipelines (the main event)
# ============================================================================


@app.post(
    "/api/v1/pipelines/run",
    response_model=PipelineRunResponse,
    tags=["pipelines"],
    summary="Run an end-to-end URL scraping pipeline",
    description=(
        "Accepts a URL, scrapes it via WraithEngine, passes the extracted "
        "content through Xerebro AI (Ollama) for enrichment/analysis, and "
        "returns the combined output."
    ),
)
async def run_pipeline(req: PipelineRunRequest):
    """
    End-to-end pipeline: URL → Scrape → Xerebro AI Enrich → Result.

    Steps:
        1. WraithEngine scrapes the URL and extracts text content
        2. Xerebro AI reasons on the extracted content (if Ollama is available)
        3. Returns combined scraped + analyzed result
    """
    import time

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

    # Parse scraped data
    try:
        scraped_data = json.loads(scrape_result.data)
    except json.JSONDecodeError:
        scraped_data = {"raw": scrape_result.data}

    # Build a readable summary for the step log
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

        # Use custom prompt if provided, otherwise default
        custom_prompt = req.prompt or (
            "Analyze the following web page content. Extract the main topic, "
            "key entities (people, organizations, products), and provide a "
            "one-paragraph summary."
        )

        # Build context from scraped content
        context = {
            "url": req.url,
            "title": scraped_data.get("title", ""),
            "body_text": scraped_data.get("body_text", "")[:10000],  # 10K chars max
            "status_code": scraped_data.get("status_code"),
        }

        logger.info(
            "Pipeline %s: Xerebro reasoning with model %s",
            pipeline_id,
            req.xerebro_model or XEREBRO_BRAIN.config.model,
        )

        # If a custom model was requested, create a temporary config
        brain = XEREBRO_BRAIN
        if req.xerebro_model and req.xerebro_model != brain.config.model:
            brain = XerebroBrain(
                XerebroConfig(model=req.xerebro_model)
            )

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

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------
    total_duration = (time.time() - overall_start) * 1000

    return PipelineRunResponse(
        pipeline_id=pipeline_id,
        url=req.url,
        status="success",
        total_duration_ms=round(total_duration, 1),
        steps=steps,
        scraped_content={
            "title": scraped_data.get("title"),
            "body_text": scraped_data.get("body_text", "")[:500],  # preview
            "status_code": scraped_data.get("status_code"),
            "content_type": scraped_data.get("content_type"),
        },
        xerebro_analysis=xerebro_analysis,
        xerebro_available=xerebro_available,
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