#!/bin/sh
# Checks the licenses of every installed npm package against the rule file.
#
# Run inside the dev container after "npm ci":
#   docker compose -f deploy/compose/compose.web.yaml run --rm web-dev npm run licenses
#
# Optional first argument: path of another rule file (used for counter-checks):
#   npm run licenses -- /path/to/rules.txt
# Prints every package with its license and a count per license.
# Exit code 0 only if every package is covered by the rule file.
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
web_dir=$(dirname -- "$script_dir")
rules=${1:-"$script_dir/license-rules.txt"}
checker="$web_dir/node_modules/.bin/license-checker-rseidelsohn"

if [ ! -r "$rules" ]; then
    echo "ERROR: rule file not readable: $rules" >&2
    exit 2
fi
if [ ! -x "$checker" ]; then
    echo "ERROR: license-checker-rseidelsohn is not installed; run \"npm ci\" first" >&2
    exit 2
fi

all=$(mktemp)
prod=$(mktemp)
trap 'rm -f "$all" "$prod"' EXIT

"$checker" --start "$web_dir" --csv > "$all"
# The production tree decides where "allow-dev" and "except-dev" are valid.
"$checker" --start "$web_dir" --production --csv > "$prod"

awk '
function trim(s) {
    sub(/^[ \t\r]+/, "", s)
    sub(/[ \t\r]+$/, "", s)
    return s
}
function fail(msg) {
    problems[++bad] = msg
}
function allowed_one(lic, dev) {
    return (lic in allow) || (dev && (lic in allow_dev))
}
function allowed(lic, dev,    s, n, parts, i) {
    if (allowed_one(lic, dev)) return 1
    s = lic
    if (s ~ /^\(.*\)$/) s = substr(s, 2, length(s) - 2)
    # Nested or mixed expressions are not evaluated: list them verbatim.
    if (s ~ /[()]/ || s ~ / WITH / || (s ~ / OR / && s ~ / AND /)) return 0
    if (s ~ / OR /) {
        n = split(s, parts, / OR /)
        for (i = 1; i <= n; i++) if (allowed_one(parts[i], dev)) return 1
        return 0
    }
    if (s ~ / AND /) {
        n = split(s, parts, / AND /)
        for (i = 1; i <= n; i++) if (!allowed_one(parts[i], dev)) return 0
        return 1
    }
    return 0
}
# Reads one CSV line of the checker into pkg_id and pkg_lic; returns 0 on failure.
function read_line(line,    n, f) {
    sub(/\r$/, "", line)
    n = 0
    if (line ~ /^".*"$/) n = split(substr(line, 2, length(line) - 2), f, "\",\"")
    if (n != 3 || f[1] !~ /.@[^@]+$/) return 0
    pkg_id = f[1]
    pkg_lic = f[2]
    return 1
}

src == "rules" {
    line = trim($0)
    if (line == "" || line ~ /^#/) next
    n = split(line, f, "|")
    for (i = 1; i <= n; i++) f[i] = trim(f[i])
    if ((f[1] == "allow" || f[1] == "allow-dev") && n == 2 && f[2] != "") {
        if (toupper(f[2]) == "UNKNOWN" || toupper(f[2]) == "UNLICENSED") {
            fail("rule file line " FNR ": " f[2] " cannot be allowed in general")
        } else if (f[1] == "allow") {
            allow[f[2]] = 1
        } else {
            allow_dev[f[2]] = 1
        }
    } else if ((f[1] == "except" || f[1] == "except-dev") && n == 5 && f[2] != "" && f[3] != "" && f[4] != "" && f[5] != "") {
        exc[f[2]] = f[3]
        exc_dev_only[f[2]] = (f[1] == "except-dev")
    } else {
        fail("rule file line " FNR ": not understood: " line)
    }
    next
}

FNR == 1 {
    if ($0 != "\"module name\",\"license\",\"repository\"") fail("unexpected header from the checker (" src "): " $0)
    next
}

src == "prod" {
    if (read_line($0)) {
        in_prod[pkg_id] = 1
    } else {
        fail("cannot read line " FNR " of the production list: " $0)
    }
    next
}

src == "all" {
    if (!read_line($0)) {
        fail("cannot read line " FNR " of the package list: " $0)
        next
    }
    name = pkg_id
    sub(/@[^@]+$/, "", name)
    dev = !(pkg_id in in_prod)
    total++
    count[pkg_lic]++
    note = ""
    if (name in exc) {
        used[name] = 1
        if (pkg_lic != exc[name]) {
            fail(pkg_id ": license \"" pkg_lic "\" differs from the named exception \"" exc[name] "\"")
        } else if (exc_dev_only[name] && !dev) {
            fail(pkg_id ": the exception is valid for development and build only, but the package is in the production tree")
        } else {
            note = "  [named exception]"
        }
    } else if (!allowed(pkg_lic, dev)) {
        if (allowed(pkg_lic, 1)) {
            fail(pkg_id ": license \"" pkg_lic "\" is allowed for development and build only, but the package is in the production tree")
        } else {
            fail(pkg_id ": license \"" pkg_lic "\" is not allowed")
        }
    }
    printf "%-10s %-48s %s%s\n", (dev ? "dev" : "production"), pkg_id, pkg_lic, note
}

END {
    if (total == 0) fail("the checker reported no packages")
    print ""
    print "Packages per license:"
    sorter = "sort -k1,1nr -k2"
    for (lic in count) printf "  %4d  %s\n", count[lic], lic | sorter
    close(sorter)
    print "  ----"
    printf "  %4d  packages\n", total
    for (name in exc) if (!(name in used)) print "Note: exception for \"" name "\" matches no installed package."
    if (bad > 0) {
        print ""
        print "License check FAILED (" bad "):"
        for (i = 1; i <= bad; i++) print "  " problems[i]
        exit 1
    }
    print ""
    print "License check passed."
}
' src=rules "$rules" src=prod "$prod" src=all "$all"
