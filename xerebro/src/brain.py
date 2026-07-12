"""
Xerebro AI — Local LLM Integration for Supra-Codex Engine

Connects to a local Ollama instance to provide LLM reasoning
capabilities for pipeline decisions: what to scrape, how to parse,
when to enrich, how to transform data.

Philosophy: local-first, private, autonomous. No API keys needed.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("xerebro")


@dataclass
class XerebroConfig:
    """Configuration for the Xerebro AI brain."""

    ollama_host: str = "http://localhost:11434"
    model: str = "llama3.2"  # Default model; user can swap
    timeout_seconds: int = 60
    max_retries: int = 3
    system_prompt: str = (
        "You are Xerebro, the AI brain of Supra-Codex Engine. "
        "You help orchestrate automation pipelines: analyzing web content, "
        "deciding data extraction strategies, and enriching results. "
        "Respond with concise, actionable JSON when possible."
    )


@dataclass
class XerebroRequest:
    """A reasoning request to the LLM."""

    prompt: str
    context: Optional[Dict[str, Any]] = None
    temperature: float = 0.1  # Low temp for deterministic decisions
    max_tokens: int = 1024
    format: str = "json"  # Request JSON mode from Ollama


@dataclass
class XerebroResponse:
    """Response from the LLM brain."""

    success: bool
    content: str
    model: str
    tokens_used: int
    error: Optional[str] = None


class XerebroBrain:
    """
    Xerebro AI Brain — connects to local Ollama for LLM reasoning.

    Handles prompt construction, request dispatch, response parsing,
    and automatic retries. Designed to be called from the engine's
    task handlers for enrichment and decision-making.

    Usage:
        brain = XerebroBrain()

        # Async:
        ok = await brain.check_availability()
        resp = await brain.reason(XerebroRequest(prompt="..."))

        # Sync convenience:
        ok = brain.check_sync()
        resp = brain.reason_sync("Extract product names from this text", {"text": "..."})
    """

    def __init__(self, config: Optional[XerebroConfig] = None):
        self.config = config or XerebroConfig()
        self._session = None  # Lazy-initialized HTTP session
        self._available = False
        logger.info(
            "XerebroBrain initialized (host=%s, model=%s)",
            self.config.ollama_host,
            self.config.model,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Sync convenience — for use in sync contexts (API endpoints, scripts)
    # ──────────────────────────────────────────────────────────────────────────

    def check_sync(self) -> bool:
        """
        Synchronous health check against the local Ollama instance.

        Returns True if Ollama is reachable and ready.
        """
        import httpx

        try:
            with httpx.Client(
                base_url=self.config.ollama_host,
                timeout=10,
            ) as client:
                resp = client.get("/api/tags")
                self._available = resp.status_code == 200
                return self._available
        except Exception as e:
            logger.warning("Ollama sync check failed: %s", e)
            self._available = False
            return False

    def reason_sync(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        format: str = "json",
    ) -> XerebroResponse:
        """
        Synchronous convenience method to send a prompt to Ollama.

        Args:
            prompt: The task description for the LLM.
            context: Optional context dict (will be formatted into the prompt).
            temperature: LLM temperature (lower = more deterministic).
            max_tokens: Maximum tokens in the response.
            format: "json" for structured JSON output, "text" for freeform.

        Returns:
            XerebroResponse with the LLM's answer.
        """
        import httpx

        if not self._available:
            self.check_sync()

        request = XerebroRequest(
            prompt=prompt,
            context=context,
            temperature=temperature,
            max_tokens=max_tokens,
            format=format,
        )

        payload = {
            "model": self.config.model,
            "prompt": self._build_prompt(request),
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        if request.format == "json":
            payload["format"] = "json"

        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(
                    "Xerebro reasoning (attempt %d/%d): %s...",
                    attempt + 1,
                    self.config.max_retries,
                    prompt[:80],
                )

                with httpx.Client(
                    base_url=self.config.ollama_host,
                    timeout=self.config.timeout_seconds,
                ) as client:
                    resp = client.post("/api/generate", json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                response_text = data.get("response", "")
                tokens_used = data.get("eval_count", 0)

                return XerebroResponse(
                    success=True,
                    content=response_text,
                    model=self.config.model,
                    tokens_used=tokens_used,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Xerebro attempt %d failed: %s", attempt + 1, last_error
                )

        return XerebroResponse(
            success=False,
            content="",
            model=self.config.model,
            tokens_used=0,
            error=last_error,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Async API (for async-first contexts)
    # ──────────────────────────────────────────────────────────────────────────

    async def _ensure_session(self):
        """Lazy-init an HTTPX async client."""
        if self._session is None:
            import httpx

            self._session = httpx.AsyncClient(
                base_url=self.config.ollama_host,
                timeout=self.config.timeout_seconds,
            )

    async def check_availability(self) -> bool:
        """Check if the local Ollama instance is reachable."""
        try:
            await self._ensure_session()
            resp = await self._session.get("/api/tags")
            self._available = resp.status_code == 200
            return self._available
        except Exception as e:
            logger.warning("Ollama not available: %s", e)
            self._available = False
            return False

    async def reason(self, request: XerebroRequest) -> XerebroResponse:
        """
        Send a reasoning request to the LLM (async).

        Args:
            request: The prompt and parameters for the LLM.

        Returns:
            Parsed response with extracted content.
        """
        await self._ensure_session()

        if not self._available:
            # Try a quick availability check
            await self.check_availability()

        payload = {
            "model": self.config.model,
            "prompt": self._build_prompt(request),
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        if request.format == "json":
            payload["format"] = "json"

        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(
                    "Xerebro reasoning (attempt %d/%d): %s...",
                    attempt + 1,
                    self.config.max_retries,
                    request.prompt[:80],
                )

                resp = await self._session.post("/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()

                response_text = data.get("response", "")
                tokens_used = data.get("eval_count", 0)

                return XerebroResponse(
                    success=True,
                    content=response_text,
                    model=self.config.model,
                    tokens_used=tokens_used,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Xerebro attempt %d failed: %s", attempt + 1, last_error
                )

        return XerebroResponse(
            success=False,
            content="",
            model=self.config.model,
            tokens_used=0,
            error=last_error,
        )

    def _build_prompt(self, request: XerebroRequest) -> str:
        """Build a structured prompt with system context."""
        parts = [self.config.system_prompt]

        if request.context:
            context_str = json.dumps(request.context, indent=2)
            parts.append(f"\nContext:\n{context_str}")

        parts.append(f"\nTask:\n{request.prompt}")

        if request.format == "json":
            parts.append("\n\nRespond with valid JSON only, no markdown.")

        return "\n".join(parts)

    async def close(self):
        """Clean up the HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None

    @property
    def is_available(self) -> bool:
        return self._available


# Convenience factory
async def create_brain(config: Optional[XerebroConfig] = None) -> XerebroBrain:
    """Create and verify a XerebroBrain instance."""
    brain = XerebroBrain(config)
    await brain.check_availability()
    return brain