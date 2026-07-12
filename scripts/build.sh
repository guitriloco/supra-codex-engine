#!/bin/bash
# Build script for Supra-Codex Engine
# Usage: ./scripts/build.sh [--clean] [--release] [--test]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_ROOT}/core/build"

echo "=== Supra-Codex Engine Build ==="
echo "Project root: ${PROJECT_ROOT}"

# Parse arguments
BUILD_TYPE="Debug"
CLEAN=false
RUN_TESTS=false

for arg in "$@"; do
    case "$arg" in
        --release) BUILD_TYPE="Release" ;;
        --clean) CLEAN=true ;;
        --test) RUN_TESTS=true ;;
        *) echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

# Clean build directory if requested
if [ "$CLEAN" = true ] && [ -d "$BUILD_DIR" ]; then
    echo "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
fi

# Configure
echo "Configuring CMake (${BUILD_TYPE})..."
cmake -S "${PROJECT_ROOT}/core" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" \
    -DBUILD_TESTS=ON \
    -DBUILD_PYTHON_BINDINGS=OFF

# Build
echo "Building..."
cmake --build "$BUILD_DIR" --parallel "$(nproc)"

echo "Build complete!"

# Run tests
if [ "$RUN_TESTS" = true ]; then
    echo "Running tests..."
    cd "$BUILD_DIR"
    ctest --output-on-failure
fi