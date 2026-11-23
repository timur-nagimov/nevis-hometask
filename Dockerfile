# Nevis Search API image. A helper stage that only provides the uv binary, then the stages of spec section 9:
#
#   uv       the pinned uv binary, a COPY source only
#   deps     locked runtime dependencies in /opt/venv                 (uv sync --locked --no-dev)
#   model    the embedding model in /opt/models                       (step 1: an empty stub; step 3 fills it)
#   app      Python + venv + model + code, non-root user, build-time check
#   test     app + dev dependencies + tests       docker compose --profile test run --rm --no-deps tests
#   runtime  app + start command; LAST, so it is the default target   docker compose up --build -d
#
# Portable between Docker BuildKit and podman/buildah (research/_reports/containers-spike.md section 3):
# fully qualified image names; files are COPYed, never bind-mounted; no HEALTHCHECK instruction (podman drops
# it; docker-compose.yml defines the health checks). The two base images are build arguments so that the
# linux/amd64 check can pin them by digest without re-tagging the local arm64 images.

ARG PYTHON_IMAGE=docker.io/library/python:3.14-slim-trixie
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.9

# ------------------------------------------------------------------------------------------------ uv
FROM ${UV_IMAGE} AS uv

# ---------------------------------------------------------------------------------------------- deps
FROM ${PYTHON_IMAGE} AS deps
COPY --from=uv /uv /bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app
# Only these two files: the layer is rebuilt when a dependency changes, not when the code does.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# --------------------------------------------------------------------------------------------- model
FROM ${PYTHON_IMAGE} AS model
# Step 1 stub: an empty model directory. Step 3 replaces this stage with scripts/fetch_model.py.
RUN mkdir -p /opt/models/leaf-ir

# ----------------------------------------------------------------------------------------------- app
FROM ${PYTHON_IMAGE} AS app
RUN groupadd --gid 10001 app \
 && useradd --uid 10001 --gid app --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ORT_DISABLE_TELEMETRY=1 \
    HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1
COPY --from=deps /opt/venv /opt/venv
COPY --from=model /opt/models /opt/models
WORKDIR /app
COPY app ./app
USER 10001:10001
# Build-time check as the user the service runs as (step 1 stub; step 3 adds the model self-check):
# the code imports, and the application can be created without any settings.
RUN python -c "from app.main import create_app; create_app()"

# ---------------------------------------------------------------------------------------------- test
FROM app AS test
USER root
COPY --from=uv /uv /bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project
COPY tests ./tests
USER 10001:10001
# /app is not writable for this user: no pytest cache directory
CMD ["pytest", "-p", "no:cacheprovider"]

# ------------------------------------------------------------------------------------------- runtime
FROM app AS runtime
EXPOSE 8000
CMD ["python", "-m", "app"]
