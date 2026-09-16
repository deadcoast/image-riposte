#!/usr/bin/env bash
# Local source installer / launcher. No artwork mutation on launch.
set -euo pipefail
PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 1 ]]; then
  printf 'Usage: bash START.sh /existing/artwork/folder [--lab]\n' >&2
  exit 2
fi
ARTWORK="$1"
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
[[ "${2:-}" != '--lab' ]] || TARGET="$PROJECT[lab]"
if [[ "$EXPECTED" != "$INSTALLED" || "${2:-}" == '--lab' ]]; then
  "$PYTHON" -m pip install "$TARGET"
fi
exec "$PYTHON" -m riposte serve "$ARTWORK"
