# Two targets:
#   dev      development and CI tooling, runs as root so that writes to the
#            bind-mounted source tree work on every host
#   runtime  application only, no development tools, runs as non-root (default)

ARG PYTHON_IMAGE=python:3.14.10-slim
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.9

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS base
# The virtual environment lives outside /app, so a bind mount of the source
# tree over /app never hides the installed tools.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=twox.config.settings
WORKDIR /app

FROM base AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1
COPY pyproject.toml uv.lock ./

FROM builder AS runtime-deps
RUN uv sync --locked --no-dev

FROM builder AS dev
# Tool caches go to /tmp, never into the bind-mounted source tree.
ENV MYPY_CACHE_DIR=/tmp/mypy_cache \
    RUFF_CACHE_DIR=/tmp/ruff_cache \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest_cache"
RUN uv sync --locked
COPY . .
CMD ["python", "manage.py", "check"]

FROM base AS runtime
RUN groupadd --system --gid 10001 twox \
    && useradd --system --uid 10001 --gid twox --no-create-home --shell /usr/sbin/nologin twox
COPY --from=runtime-deps /opt/venv /opt/venv
COPY manage.py ./
COPY twox ./twox
USER twox
# Placeholder until the ASGI server arrives with the API service.
CMD ["python", "manage.py", "check"]
