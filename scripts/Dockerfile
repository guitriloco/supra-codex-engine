# Multi-stage Docker build for Supra-Codex Engine
#
# Stage 1: Build the C++ core
# Stage 2: Runtime image with API + Engine

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM ubuntu:22.04 AS builder

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    cmake \
    libcurl4-openssl-dev \
    libssl-dev \
    libspdlog-dev \
    nlohmann-json3-dev \
    libgtest-dev \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY core/ ./core/

RUN cmake -S core -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTS=OFF \
    -DBUILD_PYTHON_BINDINGS=OFF \
    && cmake --build build --parallel "$(nproc)" \
    && cmake --install build --prefix /install

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM ubuntu:22.04 AS runtime

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    libcurl4 \
    libssl3 \
    libspdlog1 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app
COPY api/ ./api/
COPY xerebro/ ./xerebro/
COPY modules/ ./modules/
COPY bindings/ ./bindings/

# The API imports `wraith.engine` (pure-Python reference) and `modules`,
# so both must be importable from the app root.
ENV PYTHONPATH=/app:/app/bindings/python

RUN pip3 install -r api/requirements.txt && \
    pip3 install -r xerebro/requirements.txt && \
    pip3 install -r modules/requirements.txt

EXPOSE 8000

CMD ["python3", "api/main.py"]