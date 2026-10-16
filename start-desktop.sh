#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/python3 ]]; then
  python3 -m venv .venv
fi

if ! .venv/bin/python3 -c "import PySide6" 2>/dev/null; then
  .venv/bin/pip install -r requirements.txt
fi

# X11/XWayland suele ser más estable con Qt en Fedora+Wayland
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"

exec .venv/bin/python3 romsfun_gui.py
