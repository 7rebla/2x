# Build context: the repository root (see .dockerignore there, a positive
# list that admits backend/ and web/ only).
#
# Two targets:
#   dev      development and CI tooling, runs as root so that writes to the
#            bind-mounted source tree work on every host; needs no web build;
#            has GNU gettext for makemessages and the tests
#   runtime  application plus the built web UI and the compiled translation
#            catalogues, no development tools, no Node and no gettext, runs
#            as non-root (default)

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

# GNU gettext (msgfmt, xgettext, msgmerge, msgattrib), the tools behind
# makemessages and compilemessages. Licence: the programs are GPL, libintl is
# LGPL. Allowed as a tool in the dev image and in the stage locale-build only
# (E-46): never in the runtime image, never linked into the project. The
# runtime reads the compiled catalogues with Python's own gettext module.
# Debian trixie ships gettext 0.23.1.
FROM builder AS dev
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*
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
# @tanstack/query-core, @xyflow/react with @xyflow/system, classcat, zustand,
# react-compiler-runtime and the d3 modules it uses: d3-color, d3-dispatch,
# d3-drag, d3-ease, d3-interpolate, d3-selection, d3-timer, d3-transition,
# d3-zoom), the API client that @hey-api/openapi-ts copies from
# its templates into src/api/generated (including the TanStack Query options),
# the module preload helper Vite inlines and the base styles Tailwind CSS
# emits. The dependencies of react-router and @xyflow/react get a notice even
# where the bundler drops parts of them.
# react-compiler-runtime ships without a licence file; its package.json says
# MIT and its source header refers to the licence file of the facebook/react
# repository, which is the same file the react package ships. The notice
# therefore quotes react's licence file for it.
# The build fails if the production dependencies change, so that a new
# runtime package cannot ship without its notice.
# npm also lists typescript, @types/react, @types/react-dom and csstype here:
# i18next, react-i18next, react-router, @tanstack/react-query and
# @xyflow/react declare typescript, @types/react or @types/react-dom as
# optional peer dependencies, and the dev install satisfies them. The six
# @types/d3-* packages are regular dependencies of @xyflow/system. All of them
# are type information only, nothing of them reaches the bundle, so they get
# no notice.
# The font Inter 4.1 (SIL OFL 1.1, E-50) is not an npm package: its file lies
# in web/src/assets/fonts/inter/ and is shipped unchanged. The build checks
# that the file and the copy Vite emits match the SHA-256 of the release
# file, and quotes the licence text next to the font.
RUN set -eu; \
    font=src/assets/fonts/inter/InterVariable.woff2; \
    echo "693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3  $font" | sha256sum -c -; \
    emitted=$(find dist/assets -maxdepth 1 -name 'InterVariable-*.woff2'); \
    if [ -z "$emitted" ] || ! cmp -s "$font" "$emitted"; then echo "Inter missing or changed in dist/assets" >&2; exit 1; fi; \
    runtime=$(npm ls --omit=dev --all --parseable | sed -n 's|^/web/node_modules/||p' | sort | tr '\n' ' '); \
    if [ "$runtime" != "@remix-run/route-pattern @tanstack/query-core @tanstack/react-query @types/d3-color @types/d3-drag @types/d3-interpolate @types/d3-selection @types/d3-transition @types/d3-zoom @types/react @types/react-dom @xyflow/react @xyflow/system classcat cookie-es csstype d3-color d3-dispatch d3-drag d3-ease d3-interpolate d3-selection d3-timer d3-transition d3-zoom html-parse-stringify i18next react react-compiler-runtime react-dom react-i18next react-router scheduler typescript zustand " ]; then \
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
        for pkg in react react-dom scheduler i18next react-i18next html-parse-stringify react-router cookie-es @remix-run/route-pattern @tanstack/react-query @tanstack/query-core @xyflow/react @xyflow/system classcat zustand react-compiler-runtime d3-color d3-dispatch d3-drag d3-ease d3-interpolate d3-selection d3-timer d3-transition d3-zoom @hey-api/openapi-ts vite tailwindcss; do \
            dir=node_modules/$pkg; \
            case "$pkg" in \
                react-compiler-runtime) licence_file=node_modules/react/LICENSE;; \
                *) licence_file=$(find "$dir" -maxdepth 1 -type f -iname 'licen[cs]e*' | sort | head -n 1);; \
            esac; \
            if [ -z "$licence_file" ]; then echo "No licence file in $dir" >&2; exit 1; fi; \
            echo; \
            echo "------------------------------------------------------------"; \
            node -e 'const p = require(process.argv[1]); console.log(p.name + " " + p.version + " (" + p.license + ")"); console.log(typeof p.homepage === "string" ? p.homepage : "");' "./$dir/package.json"; \
            case "$pkg" in \
                @hey-api/openapi-ts) echo "Used for: the generated API client (src/api/generated), copied from the generator's templates.";; \
                vite) echo "Used for: the module preload helper that the build inlines into the bundle.";; \
                tailwindcss) echo "Used for: the base styles in the generated stylesheet.";; \
                react-compiler-runtime) echo "Used for: runtime dependency of the web interface (map page). The package has no licence file; quoted below is the licence file of the facebook/react repository its source header refers to, as shipped with the react package.";; \
                *) echo "Used for: runtime dependency of the web interface.";; \
            esac; \
            echo "------------------------------------------------------------"; \
            echo; \
            cat "$licence_file"; \
        done; \
        echo; \
        echo "------------------------------------------------------------"; \
        echo "Inter 4.1 (OFL-1.1)"; \
        echo "https://github.com/rsms/inter"; \
        echo "Used for: the font of the web interface (${emitted#dist/}), shipped unchanged."; \
        echo "------------------------------------------------------------"; \
        echo; \
        cat src/assets/fonts/inter/LICENSE.txt; \
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

# Compiles the translation catalogues (backend/locale/*/LC_MESSAGES/*.po) with
# compilemessages, which runs msgfmt from GNU gettext (see the stage dev for
# the licence). Compiled .mo files exist only in images, never in the
# repository or the bind-mounted source tree (E-34, E-46). Only the .mo files
# leave this stage. As in the stage static, the two variables exist only for
# this command.
FROM base AS locale-build
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*
COPY --from=runtime-deps /opt/venv /opt/venv
COPY backend/manage.py ./
COPY backend/twox ./twox
COPY backend/locale ./locale
RUN set -eu; \
    TWOX_SECRET_KEY=compilemessages-only TWOX_DB_PASSWORD=compilemessages-only \
        python manage.py compilemessages; \
    find locale -type f ! -name '*.mo' -delete; \
    test -n "$(find locale -type f -name '*.mo')"

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
# The compiled catalogues only (LOCALE_PATHS = /app/locale); no gettext here.
COPY --from=locale-build /app/locale ./locale
USER twox
EXPOSE 8000
# Django has no ASGI lifespan handler, so uvicorn does not need to probe for one.
# Migrations are not run here: the compose service `migrate` applies them once
# before any API instance starts.
CMD ["uvicorn", "twox.config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--lifespan", "off"]
