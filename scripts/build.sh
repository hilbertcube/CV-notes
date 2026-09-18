#!/usr/bin/env bash
# Recompile the CV notes with latexmk.
#
#   scripts/build.sh                 # rebuild every part that is out of date
#   scripts/build.sh part3 part5     # rebuild only matching parts (substring match)
#   scripts/build.sh -f              # force a full rebuild, ignoring timestamps
#   scripts/build.sh -c              # delete aux files in build/, keep the PDFs
#   scripts/build.sh -C              # delete aux files and the PDFs
#   scripts/build.sh -j 1            # serial build (default: all parts at once)
#   scripts/build.sh -v              # stream latexmk output instead of summarising
#
# Aux files land in build/ and the PDFs next to the sources; see .latexmkrc.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root" || exit 1

force=0 clean=0 cleanall=0 jobs=0 verbose=0
while getopts ":fcCj:vh" opt; do
  case "$opt" in
    f) force=1 ;;
    c) clean=1 ;;
    C) cleanall=1 ;;
    j) jobs=$OPTARG ;;
    v) verbose=1 ;;
    h) sed -n '2,/^[^#]/p' "$0" | sed -n 's/^# \?//p'; exit 0 ;;
    \?) echo "unknown option: -$OPTARG (try -h)" >&2; exit 2 ;;
    :) echo "-$OPTARG needs an argument" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

command -v latexmk >/dev/null || { echo "latexmk not found on PATH" >&2; exit 127; }

# Which parts to build: every part*.tex, or just the ones named on the command line.
mapfile -t all < <(ls part*.tex 2>/dev/null | sort)
((${#all[@]})) || { echo "no part*.tex found in $root" >&2; exit 1; }

targets=()
if (($#)); then
  for pat in "$@"; do
    hit=0
    for f in "${all[@]}"; do
      if [[ $f == *"${pat%.tex}"* ]]; then targets+=("$f"); hit=1; fi
    done
    ((hit)) || { echo "no part matches '$pat'" >&2; exit 1; }
  done
else
  targets=("${all[@]}")
fi

if ((clean || cleanall)); then
  flag=$( ((cleanall)) && echo -C || echo -c )
  latexmk "$flag" "${targets[@]}" >/dev/null 2>&1
  rmdir build 2>/dev/null
  echo "cleaned ${#targets[@]} part(s) ($flag)"
  exit 0
fi

mkdir -p build
logdir=$(mktemp -d)
trap 'rm -rf "$logdir"' EXIT

opts=(-pdf -interaction=nonstopmode -halt-on-error -file-line-error)
((force)) && opts+=(-gg)

# jobs=0 means "all at once"; latexmk itself is single-threaded per document.
((jobs > 0)) || jobs=${#targets[@]}

build_one() {
  local tex=$1 log=$logdir/${1%.tex}.log
  if ((verbose)); then
    latexmk "${opts[@]}" "$tex"
  else
    latexmk "${opts[@]}" "$tex" >"$log" 2>&1
  fi
}

declare -A pid_of
failed=() running=0
start=$SECONDS

for tex in "${targets[@]}"; do
  while ((running >= jobs)); do
    wait -n 2>/dev/null
    running=$((running - 1))
  done
  build_one "$tex" &
  pid_of["$tex"]=$!
  running=$((running + 1))
done

for tex in "${targets[@]}"; do
  if wait "${pid_of[$tex]}"; then
    printf '  ok    %s\n' "${tex%.tex}.pdf"
  else
    failed+=("$tex")
    printf '  FAIL  %s\n' "$tex"
    # Show the TeX errors: file:line:message lines, plus anything after a bare '!'.
    if ((!verbose)); then
      grep -E '^(\./)?[^ ]+\.(tex|sty):[0-9]+:|^! ' "$logdir/${tex%.tex}.log" \
        | head -20 | sed 's/^/        /'
    fi
  fi
done

printf '%d/%d built in %ds\n' \
  $((${#targets[@]} - ${#failed[@]})) "${#targets[@]}" $((SECONDS - start))
((${#failed[@]} == 0)) || exit 1
