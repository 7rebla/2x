#!/bin/sh
# Checks the licenses of every installed Python package against the rule file.
#
# Run inside the dev container, from the backend directory:
#   docker compose run --rm backend-dev sh scripts/check-licenses.sh
#
# Optional first argument: path of another rule file (used for counter-checks).
# Prints every package with its license and a count per license.
# Exit code 0 only if every package is covered by the rule file.
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
rules=${1:-"$script_dir/license-rules.txt"}

if [ ! -r "$rules" ]; then
    echo "ERROR: rule file not readable: $rules" >&2
    exit 2
fi

report=$(mktemp)
trap 'rm -f "$report"' EXIT

# --with-system: pip-licenses hides itself, prettytable and wcwidth otherwise.
pip-licenses --with-system --from=mixed --format=csv > "$report"

awk '
function trim(s) {
    sub(/^[ \t\r]+/, "", s)
    sub(/[ \t\r]+$/, "", s)
    return s
}
function fail(msg) {
    problems[++bad] = msg
}
# PEP 503: package names compare case-insensitively, "-", "_" and "." are equal.
function norm(name) {
    name = tolower(name)
    gsub(/[-_.]+/, "-", name)
    return name
}
function allowed(lic,    s, n, parts, i) {
    if (lic in allow) return 1
    s = lic
    if (s ~ /^\(.*\)$/) s = substr(s, 2, length(s) - 2)
    # Nested or mixed expressions are not evaluated: list them verbatim.
    if (s ~ /[()]/ || s ~ / WITH / || (s ~ / OR / && s ~ / AND /)) return 0
    if (s ~ / OR /) {
        n = split(s, parts, / OR /)
        for (i = 1; i <= n; i++) if (parts[i] in allow) return 1
        return 0
    }
    if (s ~ / AND /) {
        n = split(s, parts, / AND /)
        for (i = 1; i <= n; i++) if (!(parts[i] in allow)) return 0
        return 1
    }
    return 0
}

src == "rules" {
    line = trim($0)
    if (line == "" || line ~ /^#/) next
    n = split(line, f, "|")
    for (i = 1; i <= n; i++) f[i] = trim(f[i])
    if (f[1] == "allow" && n == 2 && f[2] != "") {
        if (toupper(f[2]) == "UNKNOWN" || toupper(f[2]) == "UNLICENSED") {
            fail("rule file line " FNR ": " f[2] " cannot be allowed in general")
        } else {
            allow[f[2]] = 1
        }
    } else if (f[1] == "except" && n == 5 && f[2] != "" && f[3] != "" && f[4] != "" && f[5] != "") {
        exc[norm(f[2])] = f[3]
        exc_name[norm(f[2])] = f[2]
    } else {
        fail("rule file line " FNR ": not understood: " line)
    }
    next
}

src == "report" {
    if (FNR == 1) {
        if ($0 != "\"Name\",\"Version\",\"License\"") fail("unexpected header from pip-licenses: " $0)
        next
    }
    line = $0
    sub(/\r$/, "", line)
    n = 0
    if (line ~ /^".*"$/) n = split(substr(line, 2, length(line) - 2), f, "\",\"")
    if (n != 3) {
        fail("cannot read line " FNR " of the pip-licenses output: " line)
        next
    }
    name = f[1]; version = f[2]; lic = f[3]; key = norm(name)
    total++
    count[lic]++
    note = ""
    if (key in exc) {
        used[key] = 1
        if (lic == exc[key]) {
            note = "  [named exception]"
        } else {
            fail(name " " version ": license \"" lic "\" differs from the named exception \"" exc[key] "\"")
        }
    } else if (!allowed(lic)) {
        fail(name " " version ": license \"" lic "\" is not allowed")
    }
    printf "%-28s %-18s %s%s\n", name, version, lic, note
}

END {
    if (total == 0) fail("pip-licenses reported no packages")
    print ""
    print "Packages per license:"
    sorter = "sort -k1,1nr -k2"
    for (lic in count) printf "  %4d  %s\n", count[lic], lic | sorter
    close(sorter)
    print "  ----"
    printf "  %4d  packages\n", total
    for (key in exc) if (!(key in used)) print "Note: exception for \"" exc_name[key] "\" matches no installed package."
    if (bad > 0) {
        print ""
        print "License check FAILED (" bad "):"
        for (i = 1; i <= bad; i++) print "  " problems[i]
        exit 1
    }
    print ""
    print "License check passed."
}
' src=rules "$rules" src=report "$report"
