#!/usr/bin/env bash
# Explicit setup only. Does not launch or request image locations.
set -euo pipefail
PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LAB=0
for option in "$@"; do
  case "$option" in --lab) LAB=1 ;; *) printf 'Usage: bash INSTALL.sh [--lab]\n' >&2; exit 2 ;; esac
done
printf 'RIPOSTE / Install application dependencies\nNo image folder is needed.\n'
if command -v uv >/dev/null 2>&1; then
  ARGS=(sync --frozen --inexact --project "$PROJECT")
  [[ "$LAB" == 0 ]] || ARGS+=(--extra lab)
  uv "${ARGS[@]}"
else
  PYTHON="$PROJECT/.venv/bin/python"
  [[ -x "$PYTHON" ]] || python3 -m venv "$PROJECT/.venv"
  TARGET="$PROJECT"
  [[ "$LAB" == 0 ]] || TARGET="$PROJECT[lab]"
  "$PYTHON" -m pip install --editable "$TARGET"
fi
printf 'Installed. Run bash START.sh to open the menu.\nModel weights are selected separately.\n'
