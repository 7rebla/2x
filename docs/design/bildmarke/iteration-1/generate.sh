#!/bin/sh
# Generates all SVG files of the brand mark drafts (iteration 1).
#
# Every shape is defined here with exact coordinates; run this script again
# after changing a value and all variants are rebuilt from the same geometry.
#
#   sh generate.sh        (POSIX shell, e.g. Git Bash; no other tools needed)
#
# Master grid: viewBox 0 0 64 64, content inside 4..60.
# Small grid:  viewBox 0 0 16 16, pixel-aligned (1 unit = 1 px at 16 px).
#
# Each draft is two functions, master_N and small_N, that print the SVG body.
# Argument 1 is the colour of the original, argument 2 the colour of the
# digital image (twin). Mask ids carry the draft number so that the bodies can
# also be inlined into one HTML page without clashes.
set -eu
cd "$(dirname "$0")"

# Colours (provisional, not yet approved)
PRIMARY="#765477"
LIGHT_ACCENT="#A98BAD"
DARK="#49334F"
BG_DARK="#19171D"
BG_LIGHT="#F8F6F9"

# ---------------------------------------------------------------------------
# 01 Diagonal: rounded squares, twin in front, overlap cut out of the original
# ---------------------------------------------------------------------------
master_1() {
  cat <<EOF
<defs>
  <mask id="m1" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
    <rect width="64" height="64" fill="#fff"/>
    <rect x="20" y="20" width="44" height="44" rx="12" fill="#000"/>
  </mask>
</defs>
<rect x="4" y="4" width="36" height="36" rx="8" fill="$1" mask="url(#m1)"/>
<rect x="26" y="26" width="32" height="32" rx="6" fill="none" stroke="$2" stroke-width="4"/>
<g stroke="$2" stroke-width="2" stroke-linecap="round">
  <line x1="35" y1="35" x2="49" y2="41"/>
  <line x1="35" y1="35" x2="41" y2="49"/>
  <line x1="49" y1="41" x2="41" y2="49"/>
</g>
<g fill="$2">
  <circle cx="35" cy="35" r="3"/>
  <circle cx="49" cy="41" r="3"/>
  <circle cx="41" cy="49" r="3"/>
</g>
EOF
}
small_1() {
  cat <<EOF
<defs>
  <mask id="s1" maskUnits="userSpaceOnUse" x="0" y="0" width="16" height="16">
    <rect width="16" height="16" fill="#fff"/>
    <rect x="5" y="5" width="11" height="11" rx="3" fill="#000"/>
  </mask>
</defs>
<rect x="1" y="1" width="9" height="9" rx="2" fill="$1" mask="url(#s1)"/>
<rect x="6.5" y="6.5" width="8" height="8" rx="1.5" fill="none" stroke="$2" stroke-width="1"/>
<circle cx="10.5" cy="10.5" r="1.5" fill="$2"/>
EOF
}

# ---------------------------------------------------------------------------
# 02 Side by side: upright rectangles, height offset, network cut out (negative)
# ---------------------------------------------------------------------------
master_2() {
  cat <<EOF
<defs>
  <mask id="m2" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
    <rect width="64" height="64" fill="#fff"/>
    <line x1="41" y1="28" x2="51" y2="44" stroke="#000" stroke-width="3.5" stroke-linecap="round"/>
    <circle cx="41" cy="28" r="4.5" fill="#000"/>
    <circle cx="51" cy="44" r="4.5" fill="#000"/>
  </mask>
</defs>
<rect x="6" y="8" width="24" height="40" rx="6" fill="$1"/>
<rect x="34" y="16" width="24" height="40" rx="6" fill="$2" mask="url(#m2)"/>
EOF
}
small_2() {
  cat <<EOF
<defs>
  <mask id="s2" maskUnits="userSpaceOnUse" x="0" y="0" width="16" height="16">
    <rect width="16" height="16" fill="#fff"/>
    <circle cx="12" cy="9" r="1.5" fill="#000"/>
  </mask>
</defs>
<rect x="1" y="2" width="6" height="10" rx="1.5" fill="$1"/>
<rect x="9" y="4" width="6" height="10" rx="1.5" fill="$2" mask="url(#s2)"/>
EOF
}

# ---------------------------------------------------------------------------
# 03 Circles: horizontal offset, lens cut out of the original, twin as ring
# ---------------------------------------------------------------------------
master_3() {
  cat <<EOF
<defs>
  <mask id="m3" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
    <rect width="64" height="64" fill="#fff"/>
    <circle cx="42" cy="32" r="22" fill="#000"/>
  </mask>
</defs>
<circle cx="22" cy="32" r="18" fill="$1" mask="url(#m3)"/>
<circle cx="42" cy="32" r="16" fill="none" stroke="$2" stroke-width="4"/>
<g stroke="$2" stroke-width="2" stroke-linecap="round">
  <polyline points="33,36 39,27 45,37 51,28" fill="none" stroke-linejoin="round"/>
</g>
<g fill="$2">
  <circle cx="33" cy="36" r="3"/>
  <circle cx="39" cy="27" r="3"/>
  <circle cx="45" cy="37" r="3"/>
  <circle cx="51" cy="28" r="3"/>
</g>
EOF
}
small_3() {
  cat <<EOF
<defs>
  <mask id="s3" maskUnits="userSpaceOnUse" x="0" y="0" width="16" height="16">
    <rect width="16" height="16" fill="#fff"/>
    <circle cx="10.5" cy="8" r="5.5" fill="#000"/>
  </mask>
</defs>
<circle cx="5.5" cy="8" r="4.5" fill="$1" mask="url(#s3)"/>
<circle cx="10.5" cy="8" r="4" fill="none" stroke="$2" stroke-width="1"/>
<circle cx="10.5" cy="8" r="1.5" fill="$2"/>
EOF
}

# ---------------------------------------------------------------------------
# 04 Mirror: asymmetric tab shape, mirrored at the vertical axis x = 32
# ---------------------------------------------------------------------------
master_4() {
  cat <<EOF
<path d="M4 28A13 13 0 0 1 17 15H26A4 4 0 0 1 30 19V37A4 4 0 0 1 26 41H8A4 4 0 0 1 4 37Z" fill="$1"/>
<path fill-rule="evenodd" fill="$2" d="M60 36A13 13 0 0 0 47 23H38A4 4 0 0 0 34 27V45A4 4 0 0 0 38 49H56A4 4 0 0 0 60 45Z M56 36A9 9 0 0 0 47 27H38V45H56Z"/>
<g stroke="$2" stroke-width="2" stroke-linecap="round">
  <line x1="43" y1="32" x2="43" y2="40"/>
  <line x1="43" y1="40" x2="51" y2="40"/>
</g>
<g fill="$2">
  <circle cx="43" cy="32" r="2.5"/>
  <circle cx="43" cy="40" r="2.5"/>
  <circle cx="51" cy="40" r="2.5"/>
</g>
EOF
}
small_4() {
  cat <<EOF
<path d="M1 7A3 3 0 0 1 4 4H6A1 1 0 0 1 7 5V9A1 1 0 0 1 6 10H2A1 1 0 0 1 1 9Z" fill="$1"/>
<path fill-rule="evenodd" fill="$2" d="M15 9A3 3 0 0 0 12 6H10A1 1 0 0 0 9 7V11A1 1 0 0 0 10 12H14A1 1 0 0 0 15 11Z M14 9A2 2 0 0 0 12 7H10V11H14Z"/>
<circle cx="11.5" cy="9.5" r="1" fill="$2"/>
EOF
}

# ---------------------------------------------------------------------------
# 05 Inscribed: small offset, twin outline and network as XOR with the original
# ---------------------------------------------------------------------------
master_5() {
  cat <<EOF
<defs>
  <g id="t5">
    <rect x="22" y="22" width="36" height="36" rx="6" fill="none" stroke-width="4"/>
    <line x1="31" y1="31" x2="50" y2="50" stroke-width="2" stroke-linecap="round"/>
    <circle cx="31" cy="31" r="3" stroke="none"/>
    <circle cx="40.5" cy="40.5" r="3" stroke="none"/>
    <circle cx="50" cy="50" r="3" stroke="none"/>
  </g>
  <mask id="m5a" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
    <rect width="64" height="64" fill="#fff"/>
    <use href="#t5" stroke="#000" fill="#000"/>
  </mask>
  <mask id="m5b" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
    <rect width="64" height="64" fill="#fff"/>
    <rect x="4" y="4" width="40" height="40" rx="8" fill="#000"/>
  </mask>
</defs>
<rect x="4" y="4" width="40" height="40" rx="8" fill="$1" mask="url(#m5a)"/>
<use href="#t5" stroke="$2" fill="$2" mask="url(#m5b)"/>
EOF
}
small_5() {
  cat <<EOF
<defs>
  <g id="u5">
    <rect x="5.5" y="5.5" width="9" height="9" rx="1.5" fill="none" stroke-width="1"/>
    <circle cx="8" cy="8" r="1" stroke="none"/>
    <circle cx="12" cy="12" r="1" stroke="none"/>
  </g>
  <mask id="s5a" maskUnits="userSpaceOnUse" x="0" y="0" width="16" height="16">
    <rect width="16" height="16" fill="#fff"/>
    <use href="#u5" stroke="#000" fill="#000"/>
  </mask>
  <mask id="s5b" maskUnits="userSpaceOnUse" x="0" y="0" width="16" height="16">
    <rect width="16" height="16" fill="#fff"/>
    <rect x="1" y="1" width="10" height="10" rx="2" fill="#000"/>
  </mask>
</defs>
<rect x="1" y="1" width="10" height="10" rx="2" fill="$1" mask="url(#s5a)"/>
<use href="#u5" stroke="$2" fill="$2" mask="url(#s5b)"/>
EOF
}

# ---------------------------------------------------------------------------
# 06 Behind: landscape rectangles, original in front, twin emerges behind it
# ---------------------------------------------------------------------------
master_6() {
  cat <<EOF
<defs>
  <mask id="m6" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
    <rect width="64" height="64" fill="#fff"/>
    <rect x="0" y="24" width="48" height="36" rx="10" fill="#000"/>
  </mask>
</defs>
<g mask="url(#m6)">
  <rect x="22" y="10" width="36" height="24" rx="4" fill="none" stroke="$2" stroke-width="4"/>
  <g stroke="$2" stroke-width="2" stroke-linecap="round">
    <line x1="30" y1="18" x2="42" y2="18"/>
    <line x1="42" y1="18" x2="52" y2="28"/>
  </g>
  <g fill="$2">
    <circle cx="30" cy="18" r="3"/>
    <circle cx="42" cy="18" r="3"/>
    <circle cx="52" cy="28" r="3"/>
  </g>
</g>
<rect x="4" y="28" width="40" height="28" rx="6" fill="$1"/>
EOF
}
small_6() {
  cat <<EOF
<defs>
  <mask id="s6" maskUnits="userSpaceOnUse" x="0" y="0" width="16" height="16">
    <rect width="16" height="16" fill="#fff"/>
    <rect x="0" y="6" width="12" height="10" rx="2.5" fill="#000"/>
  </mask>
</defs>
<g mask="url(#s6)">
  <rect x="5.5" y="2.5" width="9" height="6" rx="1" fill="none" stroke="$2" stroke-width="1"/>
  <circle cx="9.5" cy="4.5" r="1" fill="$2"/>
</g>
<rect x="1" y="7" width="10" height="7" rx="1.5" fill="$1"/>
EOF
}

NAMES="01-diagonal 02-nebeneinander 03-kreise 04-spiegelung 05-eingeschrieben 06-dahinter"

svg_open() { # size viewbox
  printf '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" width="%s" height="%s">\n' "$2" "$2" "$1" "$1"
}

preview() { # n kind background colour
  printf '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="192" height="192">\n'
  printf '<rect width="96" height="96" fill="%s"/>\n' "$3"
  printf '<svg x="16" y="16" width="64" height="64" viewBox="0 0 64 64">\n'
  "master_$1" "$4" "$4"
  printf '</svg>\n</svg>\n'
}

n=0
for name in $NAMES; do
  n=$((n + 1))
  mkdir -p "$name"
  f="$name/$name"
  { svg_open 64 64; "master_$n" currentColor currentColor; echo '</svg>'; } > "$f.svg"
  { svg_open 64 64; "master_$n" "#000000" "#000000"; echo '</svg>'; } > "$f-mono.svg"
  { svg_open 64 64; "master_$n" "$PRIMARY" "$DARK"; echo '</svg>'; } > "$f-aubergine.svg"
  preview "$n" dark "$BG_DARK" "$LIGHT_ACCENT" > "$f-preview-dark.svg"
  preview "$n" light "$BG_LIGHT" "$PRIMARY" > "$f-preview-light.svg"
  { svg_open 16 16; "small_$n" currentColor currentColor; echo '</svg>'; } > "$f-16.svg"
  { svg_open 16 16; "small_$n" "#000000" "#000000"; echo '</svg>'; } > "$f-16-mono.svg"
  { svg_open 16 16; "small_$n" "$PRIMARY" "$PRIMARY"; echo '</svg>'; } > "$f-16-light.svg"
  { svg_open 16 16; "small_$n" "$LIGHT_ACCENT" "$LIGHT_ACCENT"; echo '</svg>'; } > "$f-16-dark.svg"
  { svg_open 64 64; "master_$n" "$PRIMARY" "$PRIMARY"; echo '</svg>'; } > "$f-light.svg"
  { svg_open 64 64; "master_$n" "$LIGHT_ACCENT" "$LIGHT_ACCENT"; echo '</svg>'; } > "$f-dark.svg"
done
echo "generated $n drafts"

# Comparison sheets: self-contained HTML files with every SVG embedded, so
# that they open from anywhere (also as a single file without the folders).
data=$(mktemp)
{
  echo "const SVG = {"
  for f in */*.svg; do
    printf '"%s": `' "$f"
    cat "$f"
    echo '`,'
  done
  echo "};"
} > "$data"
for t in vorlagen/*.html; do
  sed -e "/\/\*SVGDATA\*\//r $data" -e '/\/\*SVGDATA\*\//d' "$t" > "$(basename "$t")"
done
rm -f "$data"
echo "generated comparison sheets"
