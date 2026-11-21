# Build context: the repository root (see .dockerignore there, a positive
# list that admits backend/ and web/ only).
#
# Two targets:
#   dev      development and CI tooling, runs as root so that writes to the
#            bind-mounted source tree work on every host; needs no web build
#   runtime  application plus the built web UI, no development tools and no
#            Node, runs as non-root (default)

ARG PYTHON_IMAGE=python:3.14.10-slim
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.9
ARG NODE_IMAGE=node:24-slim

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
COPY backend/pyproject.toml backend/uv.lock ./

FROM builder AS runtime-deps
RUN uv sync --locked --no-dev

FROM builder AS dev
# Tool caches go to /tmp, never into the bind-mounted source tree.
ENV MYPY_CACHE_DIR=/tmp/mypy_cache \
    RUFF_CACHE_DIR=/tmp/ruff_cache \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest_cache"
RUN uv sync --locked
COPY backend/ ./
CMD ["python", "manage.py", "check"]

# Builds the web UI. Only this stage has Node; nothing of it but the built
# files reaches the runtime image.
FROM ${NODE_IMAGE} AS web-build
ENV CI=true \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false
WORKDIR /web
COPY web/package.json web/package-lock.json web/.npmrc ./
RUN npm ci
COPY web/ ./
RUN npm run build
# Licence notices of everything that ends up in the shipped bundle, written
# next to the build as THIRD-PARTY-NOTICES.txt (served below /static/).
# Shipped code: the production dependencies (react, react-dom, scheduler,
# i18next, react-i18next, html-parse-stringify, react-router with cookie-es
# and @remix-run/route-pattern, @tanstack/react-query with
# @tanstack/query-core), the API client that @hey-api/openapi-ts copies from
# its templates into src/api/generated (including the TanStack Query options),
# the module preload helper Vite inlines and the base styles Tailwind CSS
# emits. The dependencies of react-router get a notice even where the bundler
# drops parts of them.
# The build fails if the production dependencies change, so that a new
# runtime package cannot ship without its notice.
# npm also lists typescript, @types/react, @types/react-dom and csstype here:
# i18next, react-i18next, react-router and @tanstack/react-query declare
# typescript, @types/react or @types/react-dom as optional peer dependencies,
# and the dev install satisfies them. They are type information only, nothing
# of them reaches the bundle, so they get no notice.
RUN set -eu; \
    runtime=$(npm ls --omit=dev --all --parseable | sed -n 's|^/web/node_modules/||p' | sort | tr '\n' ' '); \
    if [ "$runtime" != "@remix-run/route-pattern @tanstack/query-core @tanstack/react-query @types/react @types/react-dom cookie-es csstype html-parse-stringify i18next react react-dom react-i18next react-router scheduler typescript " ]; then \
        echo "Production dependencies changed ($runtime): update the notice list in backend/Dockerfile." >&2; \
        exit 1; \
    fi; \
    out=dist/THIRD-PARTY-NOTICES.txt; \
    { \
        echo "Third-party software shipped with the 2x web interface"; \
        echo "======================================================"; \
        echo; \
        echo "The files below /static/ contain code from the following packages."; \
        echo "Each section quotes the package's licence file unchanged."; \
        for pkg in react react-dom scheduler i18next react-i18next html-parse-stringify react-router cookie-es @remix-run/route-pattern @tanstack/react-query @tanstack/query-core @hey-api/openapi-ts vite tailwindcss; do \
            dir=node_modules/$pkg; \
            licence_file=$(find "$dir" -maxdepth 1 -type f -iname 'licen[cs]e*' | sort | head -n 1); \
            if [ -z "$licence_file" ]; then echo "No licence file in $dir" >&2; exit 1; fi; \
            echo; \
            echo "------------------------------------------------------------"; \
            node -e 'const p = require(process.argv[1]); console.log(p.name + " " + p.version + " (" + p.license + ")"); console.log(typeof p.homepage === "string" ? p.homepage : "");' "./$dir/package.json"; \
            case "$pkg" in \
                @hey-api/openapi-ts) echo "Used for: the generated API client (src/api/generated), copied from the generator's templates.";; \
                vite) echo "Used for: the module preload helper that the build inlines into the bundle.";; \
                tailwindcss) echo "Used for: the base styles in the generated stylesheet.";; \
                *) echo "Used for: runtime dependency of the web interface.";; \
            esac; \
            echo "------------------------------------------------------------"; \
            echo; \
            cat "$licence_file"; \
        done; \
    } > "$out"

# Collects the static files once, at image build time. Needs neither a
# database nor a real secret key: both variables exist only for this command
# and are not stored in the image.
FROM base AS static
COPY --from=runtime-deps /opt/venv /opt/venv
COPY backend/manage.py ./
COPY backend/twox ./twox
COPY --from=web-build /web/dist /web-dist
RUN TWOX_SECRET_KEY=collectstatic-only TWOX_DB_PASSWORD=collectstatic-only \
    TWOX_WEB_DIST_DIR=/web-dist \
    python manage.py collectstatic --noinput

FROM base AS runtime
RUN groupadd --system --gid 10001 twox \
    && useradd --system --uid 10001 --gid twox --no-create-home --shell /usr/sbin/nologin twox \
    && install -d -m 0750 -o twox -g twox /data/media
# /data/media is the mount point of the volume media-data (uploaded files). A
# new, empty named volume takes over owner and mode of this directory, so the
# app user can write there. Everything else, /app included, stays read-only.
COPY --from=runtime-deps /opt/venv /opt/venv
COPY backend/manage.py ./
COPY backend/twox ./twox
# Owned by root and read-only for the app user: nothing writes here at runtime.
COPY --from=static /app/staticfiles ./staticfiles
USER twox
EXPOSE 8000
# Django has no ASGI lifespan handler, so uvicorn does not need to probe for one.
# Migrations are not run here: the compose service `migrate` applies them once
# before any API instance starts.
CMD ["uvicorn", "twox.config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--lifespan", "off"]
