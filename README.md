# Supra-Codex Engine

**A modular, distributed AI orchestration platform for sovereign automation.**

Run high-performance web scraping, data enrichment, and automation pipelines on your own hardware — no expensive third-party APIs, no vendor lock-in.

## Architecture

```
supra-codex-engine/
├── core/                    # WraithEngine — C++ compute core
│   ├── include/wraith/      # Public C++ headers
│   │   ├── engine.h         # Core engine API
│   │   ├── task.h           # Task queue & lifecycle
│   │   ├── scheduler.h      # Worker thread pool
│   │   ├── resource_monitor.h # CPU/memory tracking
│   │   └── modules/         # Built-in modules (scraper, enricher, rate limiter)
│   ├── src/                 # C++ implementation
│   └── tests/               # GTest unit tests
├── bindings/python/         # Python bindings (pybind11 — WIP)
│   ├── wraith/              # Pure-Python reference implementation
│   ├── src/                 # Future native module entry point
│   └── tests/               # pytest test suite
├── api/                     # REST API server (FastAPI)
│   ├── main.py              # Application entry point & routes
│   ├── routes/              # Route modules
│   └── models/              # Pydantic models
├── xerebro/                 # Xerebro AI — Local LLM integration
│   ├── src/brain.py         # Ollama client & reasoning engine
│   ├── models/              # Request/response data models
│   └── tests/               # pytest tests
├── proto/                   # Protocol Buffers / communication schemas
└── scripts/                 # Build scripts, Dockerfiles, CI config
```

## Components

### WraithEngine (C++)
High-performance compute core. Executes tasks via a thread-pool scheduler with:
- Priority-based task queue
- Modular handler system (scrape, enrich, rate-limit, custom)
- Resource monitoring (CPU, memory, overload detection)
- Retry logic with backoff

### Xerebro AI Brain
Local-first LLM integration via **Ollama**. Provides reasoning for:
- Scraping strategy decisions (what to extract, which selectors to use)
- Data enrichment (entity extraction, classification, normalization)
- Pipeline flow decisions (when to scrape vs. enrich vs. transform)

No API keys needed — runs entirely on your hardware.

### REST API
FastAPI-based API exposing engine capabilities:
- `GET /health` — health check
- `GET /api/v1/status` — engine stats
- `POST /api/v1/engine/start` — start engine
- `POST /api/v1/engine/stop` — stop engine
- `POST /api/v1/tasks` — submit a task
- `GET /api/v1/tasks/{id}` — task status

### Python Bindings
Pythonic interface to the WraithEngine (reference implementation included; native pybind11 bindings planned):

```python
from wraith import WraithEngine, TaskConfig

engine = WraithEngine()
engine.start()

config = TaskConfig(type="scrape", target="https://example.com")
future = engine.submit_task(config)
result = future.result()
print(result.data)
```

## Quick Start

### Prerequisites
- CMake >= 3.20
- C++20 compiler (GCC 11+, Clang 14+)
- Python >= 3.9
- Ollama (optional, for Xerebro AI)

### Build C++ Core
```bash
cd core
mkdir build && cd build
cmake ..
cmake --build .
ctest  # Run tests
```

### Run API Server
```bash
cd api
pip install -r requirements.txt
python main.py
# API available at http://localhost:8000
```

### Run Python Tests
```bash
cd bindings/python
pip install -e .
pytest tests/
```

### Xerebro AI (with Ollama)
```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2

cd xerebro
pip install -r requirements.txt
python -c "import asyncio; from src.brain import XerebroBrain; asyncio.run(XerebroBrain().check_availability())"
```

## Philosophy

- **Sovereign compute** — run everything on your own hardware
- **Zero API lock-in** — no mandatory third-party services
- **Local-first AI** — LLM reasoning stays on your machine
- **Every node is autonomous** — distributed by design
- **Modular by default** — swap components without breaking pipelines

## License

Proprietary — see LICENSE file (coming soon).

---

Built by Team Supra-Codex Engine 🚀