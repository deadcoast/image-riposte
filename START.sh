#!/usr/bin/env bash
# Launch the installed interactive menu. Setup is explicit in INSTALL.sh.
set -euo pipefail
PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
IMAGES=""
BROWSER=0; LINEAR=0; MOTION=1; THEME=goks
if [[ $# -gt 0 && "$1" != --* ]]; then IMAGES="$1"; shift; fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    --lab) printf 'Run bash INSTALL.sh --lab, then bash START.sh.\n' >&2; exit 2 ;;
    --browser) BROWSER=1 ;;
    --linear) LINEAR=1 ;;
    --no-animation) MOTION=0 ;;
    --theme)
      shift
      THEME="${1:-}"
      [[ "$THEME" == goks || "$THEME" == dark || "$THEME" == light || "$THEME" == mono ]] || { printf 'Invalid palette.\n' >&2; exit 2; }
      ;;
    *) printf 'Unknown launcher option. No images changed.\n' >&2; exit 2 ;;
  esac
  shift
done
PYTHON="$PROJECT/.venv/bin/python"
[[ -x "$PYTHON" ]] || { printf 'Run bash INSTALL.sh first, then bash START.sh.\n' >&2; exit 2; }
if [[ "$BROWSER" == 1 && -z "$IMAGES" ]]; then printf 'Browser mode requires an image folder argument. Run START.sh without flags for the menu.\n' >&2; exit 2; fi
if [[ -n "$IMAGES" ]]; then
  "$PYTHON" -c "import sys;from pathlib import Path;p,r=map(lambda v:Path(v).resolve(),sys.argv[1:]);sys.exit(0 if r.is_dir() and p!=r and not p.is_relative_to(r) and not r.is_relative_to(p) else 'Use an existing image folder separate from the application.')" "$PROJECT" "$IMAGES"
fi
EXPECTED="$("$PYTHON" -c "import sys,tomllib;print(tomllib.load(open(sys.argv[1],'rb'))['project']['version'])" "$PROJECT/pyproject.toml")"
INSTALLED="$("$PYTHON" -c "import importlib.metadata as m, importlib.util as u, pathlib, sys; s=u.find_spec('riposte'); current=s is not None and s.origin is not None and pathlib.Path(s.origin).resolve()==(pathlib.Path(sys.argv[1])/'src/riposte/__init__.py').resolve(); print(next((d.version for d in m.distributions() if d.metadata['Name']=='riposte-studio'),'absent') if current else 'absent')" "$PROJECT")"
if [[ "$EXPECTED" != "$INSTALLED" ]]; then
  printf 'Refresh this checkout with bash INSTALL.sh, then bash START.sh.\n' >&2
  exit 2
fi
ARGS=(-m riposte --theme "$THEME")
[[ "$MOTION" == 1 ]] || ARGS+=(--no-animation)
[[ "$LINEAR" == 0 ]] || ARGS+=(--plain)
if [[ "$BROWSER" == 1 ]]; then ARGS+=(serve "$IMAGES"); else ARGS+=(ui); [[ -z "$IMAGES" ]] || ARGS+=("$IMAGES"); fi
exec "$PYTHON" "${ARGS[@]}"
