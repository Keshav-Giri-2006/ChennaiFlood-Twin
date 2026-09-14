# ChennaiFlood-Twin backend: FastAPI + EPA SWMM 5.2.4 (built from the official USEPA source).
# Build context: repository root (see compose.yaml):  docker build -f backend/Dockerfile .

# ---- Stage 1: build the EPA SWMM 5.2.4 command-line engine for Linux -------------------------------
FROM debian:bookworm-slim AS swmm-build
# Official USEPA repository, tag v5.2.4 pinned to its commit so the engine cannot silently change.
ARG SWMM_REPO=https://github.com/USEPA/Stormwater-Management-Model.git
ARG SWMM_COMMIT=7952ca837988b1c32f791812eccc9fd64547e093
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential cmake git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN git clone --filter=blob:none "$SWMM_REPO" /src/swmm \
 && cd /src/swmm && git checkout --detach "$SWMM_COMMIT" \
 && test "$(git rev-parse HEAD)" = "$SWMM_COMMIT"
RUN cmake -S /src/swmm -B /src/swmm/build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF \
 && cmake --build /src/swmm/build --config Release -j 2 \
 && mkdir -p /opt/swmm/bin /opt/swmm/lib \
 && find /src/swmm/build -type f -name runswmm -exec cp {} /opt/swmm/bin/ \; \
 && find /src/swmm/build \( -type f -o -type l \) -name 'libswmm5*' -exec cp -P {} /opt/swmm/lib/ \; \
 && test -x /opt/swmm/bin/runswmm

# ---- Stage 2: runtime ---------------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OPENBLAS_NUM_THREADS=1 \
    LD_LIBRARY_PATH=/opt/swmm/lib \
    APP_ENV=container \
    DATA_DIR=/app \
    RUNTIME_DIR=/app/runtime \
    SWMM_EXECUTABLE=/opt/swmm/bin/runswmm \
    SIMULATION_MAX_CONCURRENT=1

COPY --from=swmm-build /opt/swmm /opt/swmm

WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Application code and non-secret registries.
COPY backend/app ./app
COPY backend/config ./config

# Read-only project data required at runtime (checksum-pinned in backend/config/*.json):
# processed GIS/network/DEM, reconstructed conduit geometry, approved model + verified demo outputs, raw rainfall.
COPY data_processed /app/data_processed
COPY gis/ward176_reconstructed_conduits.geojson /app/gis/ward176_reconstructed_conduits.geojson
COPY simulation/ward176_hydraulic_reconstructed_candidate.inp simulation/ward176_hydraulic_reconstructed_candidate.rpt simulation/ward176_hydraulic_reconstructed_candidate.out /app/simulation/
COPY data_raw/rainfall /app/data_raw/rainfall

RUN groupadd --system app && useradd --system --gid app --home-dir /app app \
 && mkdir -p /app/runtime && chown -R app:app /app/runtime
USER app

EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"

# One worker: SQLite metadata + an in-process simulation queue (SIMULATION_MAX_CONCURRENT).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
