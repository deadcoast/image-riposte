#!/usr/bin/env bash
# Local source installer / launcher. No artwork mutation on launch.
set -euo pipefail
PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 1 ]]; then
  printf 'Usage: bash START.sh /existing/artwork/folder [--lab] [--browser] [--no-animation] [--linear] [--theme goks|dark|light|mono]\n' >&2
  exit 2
fi
ARTWORK="$1"
shift
LAB=0; BROWSER=0; LINEAR=0; MOTION=1; THEME=goks
while [[ $# -gt 0 ]]; do
  case "$1" in
    --lab) LAB=1 ;;
    --browser) BROWSER=1 ;;
    --linear) LINEAR=1 ;;
    --no-animation) MOTION=0 ;;
    --theme)
      shift
      THEME="${1:-}"
      [[ "$THEME" == goks || "$THEME" == dark || "$THEME" == light || "$THEME" == mono ]] || { printf 'Invalid palette.\n' >&2; exit 2; }
      ;;
    *) printf 'Unknown launcher option. No artwork changed.\n' >&2; exit 2 ;;
  esac
  shift
done
python3 - "$PROJECT" "$ARTWORK" <<'PY'
import sys
from pathlib import Path
project, artwork = [Path(arg).resolve() for arg in sys.argv[1:]]
if not artwork.is_dir() or project == artwork or project.is_relative_to(artwork) or artwork.is_relative_to(project):
    raise SystemExit('Use an existing artwork folder separate from the application and model folders.')
if sys.version_info < (3, 11):
    raise SystemExit('Python 3.11 or newer is required.')
PY
PYTHON="$PROJECT/.venv/bin/python"
[[ -x "$PYTHON" ]] || python3 -m venv "$PROJECT/.venv"
EXPECTED="$("$PYTHON" -c "import sys,tomllib;print(tomllib.load(open(sys.argv[1],'rb'))['project']['version'])" "$PROJECT/pyproject.toml")"
INSTALLED="$("$PYTHON" -c "import importlib.metadata as m;print(next((d.version for d in m.distributions() if d.metadata['Name']=='riposte-studio'),'absent'))")"
TARGET="$PROJECT"
[[ "$LAB" == 0 ]] || TARGET="$PROJECT[lab]"
if [[ "$EXPECTED" != "$INSTALLED" || "$LAB" == 1 ]]; then
  "$PYTHON" -m pip install "$TARGET"
fi
ARGS=(-m riposte --theme "$THEME")
[[ "$MOTION" == 1 ]] || ARGS+=(--no-animation)
[[ "$LINEAR" == 0 ]] || ARGS+=(--plain)
if [[ "$BROWSER" == 1 ]]; then ARGS+=(serve "$ARTWORK"); else ARGS+=(ui "$ARTWORK"); fi
exec "$PYTHON" "${ARGS[@]}"
