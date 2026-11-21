#!/usr/bin/env bash
# Measures file access from containers in two locations (work order 004):
#   L1  Windows folder: source tree bind-mounted from the working directory
#       (services backend-dev and web-dev, as used today)
#   L2  Linux file system: a copy of the source tree in a named Docker volume
#       (services backend-dev-vol and web-dev-vol from compose.bench.yaml)
#
# Run from anywhere, e.g. in Git Bash from the repository root:
#   bash deploy/compose/bench-file-access.sh
#
# Settings (environment variables):
#   BENCH_PROJECT  compose project name             (default: twox-bench)
#   BENCH_RUNS     warm repetitions after the cold run (default: 5)
#   BENCH_RAW      file to keep the raw measurements in (default: temporary)
#
# Everything is measured inside the containers: each step runs in a fresh
# `docker compose run --rm` container and is timed there with `date +%s%N`
# around the command, so container start-up is not part of the numbers.
# The first repetition (cold) is reported on its own; median and range come
# from the warm repetitions. L1 and L2 alternate step by step, and the order
# flips with every repetition, so that background load hits both locations
# alike. At the end all containers, volumes and built images of the project
# are removed, as are the temporary files in the bind-mounted folders.
set -euo pipefail

# Git Bash would otherwise rewrite container paths such as /app.
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")/../.."

PROJECT=${BENCH_PROJECT:-twox-bench}
RUNS=${BENCH_RUNS:-5}
FS_FILES=10000
WALK_PASSES=20

if [ ! -f .env ]; then
    echo "Copy .env.example to .env first." >&2
    exit 1
fi

dc() {
    docker compose -p "$PROJECT" --env-file .env \
        -f deploy/compose/compose.yaml \
        -f deploy/compose/compose.web.yaml \
        -f deploy/compose/compose.bench.yaml \
        --profile dev "$@"
}

log() { printf '[bench %s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }

raw=${BENCH_RAW:-$(mktemp)}
: > "$raw"

# Remember what existed before, so that cleanup removes only our own leftovers.
had_dist=0
[ -e web/dist ] && had_dist=1
had_node_modules=0
[ -e web/node_modules ] && had_node_modules=1

cleanup() {
    log "cleaning up"
    rm -rf backend/.bench-fs
    if [ "$had_dist" = 0 ]; then rm -rf web/dist; fi
    # Docker creates an empty mount point for the node_modules volume.
    if [ "$had_node_modules" = 0 ] && [ -d web/node_modules ]; then
        rmdir web/node_modules 2>/dev/null || true
    fi
    dc down --volumes --rmi local --remove-orphans >/dev/null 2>&1 || true
    if [ -z "${BENCH_RAW:-}" ]; then rm -f "$raw"; fi
}
trap cleanup EXIT

# record STEP LOCATION REP NANOSECONDS
record() {
    awk -v s="$1" -v l="$2" -v r="$3" -v ns="$4" \
        'BEGIN { printf "%s %s %s %.3f\n", s, l, r, ns / 1e9 }' >> "$raw"
}

# timed REP STEP LOCATION SERVICE COMMAND...
# Runs COMMAND in /app of a fresh container and records its duration.
timed() {
    local rep=$1 step=$2 loc=$3 svc=$4
    shift 4
    local out ns rc
    out=$(dc run --rm -T "$svc" sh -c '
        cd /app
        s=$(date +%s%N)
        "$@" > /tmp/bench.log 2>&1
        rc=$?
        e=$(date +%s%N)
        echo "BENCH_NS $((e - s)) $rc"
        if [ "$rc" -ne 0 ]; then tail -n 40 /tmp/bench.log; fi
    ' sh "$@" 2>&1) || true
    ns=$(printf '%s\n' "$out" | awk '$1 == "BENCH_NS" { print $2 }')
    rc=$(printf '%s\n' "$out" | awk '$1 == "BENCH_NS" { print $3 }')
    if [ -z "$ns" ] || [ "$rc" != 0 ]; then
        printf '%s\n' "$out" >&2
        echo "Step $step failed in $loc (repetition $rep)." >&2
        exit 1
    fi
    record "$step" "$loc" "$rep" "$ns"
    log "rep $rep  $loc  $step  $(awk -v ns="$ns" 'BEGIN { printf "%.2f s", ns / 1e9 }')"
}

# Plain file system work with the Python standard library: create, read and
# delete many small files, then list and stat the source tree several times.
FS_SCRIPT=$(cat <<PY
import os
import shutil
import time

base = "/app/.bench-fs"
files = $FS_FILES
passes = $WALK_PASSES
shutil.rmtree(base, ignore_errors=True)
os.makedirs(base)
names = [os.path.join(base, f"f{i:05d}.txt") for i in range(files)]
payload = "x" * 100

start = time.perf_counter_ns()
for name in names:
    with open(name, "w") as handle:
        handle.write(payload)
create = time.perf_counter_ns() - start

start = time.perf_counter_ns()
for name in names:
    with open(name) as handle:
        handle.read()
read = time.perf_counter_ns() - start

start = time.perf_counter_ns()
for name in names:
    os.remove(name)
delete = time.perf_counter_ns() - start
os.rmdir(base)

start = time.perf_counter_ns()
seen = 0
for _ in range(passes):
    for root, _dirs, entries in os.walk("/app"):
        for entry in entries:
            os.stat(os.path.join(root, entry))
            seen += 1
walk = time.perf_counter_ns() - start

print(f"BENCH fs-create {create}")
print(f"BENCH fs-read {read}")
print(f"BENCH fs-delete {delete}")
print(f"BENCH fs-walk-stat {walk}")
print(f"INFO stat calls {seen}")
PY
)

# fs_bench REP LOCATION SERVICE
fs_bench() {
    local rep=$1 loc=$2 svc=$3 out
    out=$(printf '%s\n' "$FS_SCRIPT" | dc run --rm -T --no-deps "$svc" python - 2>&1) || {
        printf '%s\n' "$out" >&2
        echo "File system step failed in $loc (repetition $rep)." >&2
        exit 1
    }
    while read -r tag name ns; do
        if [ "$tag" = BENCH ]; then
            record "$name" "$loc" "$rep" "$ns"
            log "rep $rep  $loc  $name  $(awk -v ns="$ns" 'BEGIN { printf "%.2f s", ns / 1e9 }')"
        fi
    done <<< "$out"
}

# step REP STEP LOCATION: dispatches one step to the service of LOCATION.
step() {
    local rep=$1 name=$2 loc=$3 backend web
    if [ "$loc" = L1 ]; then backend=backend-dev; web=web-dev
    else backend=backend-dev-vol; web=web-dev-vol; fi
    case "$name" in
        pytest)    timed "$rep" "$name" "$loc" "$backend" pytest -q ;;
        mypy)      timed "$rep" "$name" "$loc" "$backend" mypy . ;;
        ruff)      timed "$rep" "$name" "$loc" "$backend" ruff check . ;;
        django-check) timed "$rep" "$name" "$loc" "$backend" python manage.py check ;;
        npm-ci)    timed "$rep" "$name" "$loc" "$web" npm ci --prefer-offline ;;
        npm-lint)  timed "$rep" "$name" "$loc" "$web" npm run lint ;;
        npm-typecheck) timed "$rep" "$name" "$loc" "$web" npm run typecheck ;;
        npm-test)  timed "$rep" "$name" "$loc" "$web" npm run test ;;
        npm-build) timed "$rep" "$name" "$loc" "$web" npm run build ;;
        fs)        fs_bench "$rep" "$loc" "$backend" ;;
    esac
}

STEPS="pytest mypy ruff django-check npm-ci npm-lint npm-typecheck npm-test npm-build fs"
ROWS="pytest mypy ruff django-check npm-ci npm-lint npm-typecheck npm-test npm-build fs-create fs-read fs-delete fs-walk-stat"

# --- Preparation (not measured) ---------------------------------------------
log "building images"
dc build --quiet backend-dev backend-dev-vol web-dev web-dev-vol bench-seed >&2
log "starting the database"
dc up --detach --wait db >/dev/null 2>&1
log "copying the source tree into the volumes"
dc run --rm -T --no-deps bench-seed sh -c '
    set -e
    tar -C /src/backend -cf - . | tar -C /dst/backend -xf -
    tar -C /src/web --exclude=./node_modules --exclude=./dist -cf - . \
        | tar -C /dst/web -xf -
' >&2
log "filling the shared npm cache"
dc run --rm -T --no-deps web-dev-vol sh -c \
    'npm ci --prefer-offline > /dev/null 2>&1 && rm -rf node_modules' >&2

# Conditions of the measurement.
docker_server=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo unknown)
docker_platform=$(docker version --format '{{.Server.Platform.Name}}' 2>/dev/null || echo unknown)
compose_version=$(docker compose version --short 2>/dev/null || echo unknown)
vm_info=$(dc run --rm -T --no-deps backend-dev-vol sh -c 'echo "kernel $(uname -r), $(nproc) CPUs"')

# --- Measurement --------------------------------------------------------------
rep=0
while [ "$rep" -le "$RUNS" ]; do
    if [ $((rep % 2)) -eq 0 ]; then order="L1 L2"; else order="L2 L1"; fi
    for name in $STEPS; do
        for loc in $order; do
            step "$rep" "$name" "$loc"
        done
    done
    rep=$((rep + 1))
done

# --- Report -------------------------------------------------------------------
# stats STEP LOCATION -> "median min max" over the warm repetitions
stats() {
    awk -v s="$1" -v l="$2" '$1 == s && $2 == l && $3 > 0 { print $4 }' "$raw" \
        | sort -g \
        | awk '{ v[NR] = $1 }
               END {
                   if (NR == 0) { print "- - -"; exit }
                   m = (NR % 2) ? v[(NR + 1) / 2] : (v[NR / 2] + v[NR / 2 + 1]) / 2
                   printf "%.2f %.2f %.2f\n", m, v[1], v[NR]
               }'
}
cold() {
    awk -v s="$1" -v l="$2" '$1 == s && $2 == l && $3 == 0 { printf "%.2f", $4 }' "$raw"
}

echo
echo "File access benchmark ($(date -u +%Y-%m-%dT%H:%MZ))"
echo "Docker: $docker_server ($docker_platform), Compose $compose_version, VM: $vm_info"
echo "Warm repetitions: $RUNS (plus one cold run). Seconds. Factor = L1 median / L2 median."
echo "fs-*: $FS_FILES files of 100 bytes; fs-walk-stat: $WALK_PASSES passes over backend/."
echo
echo "| Step | L1 cold | L2 cold | L1 median | L1 range | L2 median | L2 range | Factor |"
echo "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
for name in $ROWS; do
    read -r m1 lo1 hi1 <<< "$(stats "$name" L1)"
    read -r m2 lo2 hi2 <<< "$(stats "$name" L2)"
    factor=$(awk -v a="$m1" -v b="$m2" 'BEGIN { if (b + 0 > 0) printf "%.2f", a / b; else print "-" }')
    printf '| %s | %s | %s | %s | %s-%s | %s | %s-%s | %s |\n' \
        "$name" "$(cold "$name" L1)" "$(cold "$name" L2)" \
        "$m1" "$lo1" "$hi1" "$m2" "$lo2" "$hi2" "$factor"
done
