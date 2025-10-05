#!/bin/bash
set -euo pipefail

APP_DIR=${APP_DIR:-"$HOME/plotter-studio"}
cd "$APP_DIR"

if [ ! -f "venv/bin/activate" ]; then
  echo "[error] Virtual environment not found. Run ./install.sh first."
  exit 1
fi

source venv/bin/activate

if [ -f "$APP_DIR/.env" ]; then
  set -a
  source "$APP_DIR/.env"
  set +a
fi

exec "$APP_DIR/venv/bin/plotterstudio" run "$@"