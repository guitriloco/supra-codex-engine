#!/bin/bash
# Docker build for Supra-Codex Engine

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Build the engine image
docker build -f "${SCRIPT_DIR}/Dockerfile" \
    -t supra-codex-engine:latest \
    -t supra-codex-engine:0.1.0 \
    "$PROJECT_ROOT"

echo "Docker image built: supra-codex-engine:latest"