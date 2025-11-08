#!/bin/bash
set -euo pipefail

APP_DIR=${APP_DIR:-"$HOME/plotter-studio"}

if [ ! -d "$APP_DIR" ]; then
  echo "[error] Plotter Studio not found at $APP_DIR"
  exit 1
fi

echo "[update] Pulling latest version..."
git -C "$APP_DIR" pull --ff-only

cd "$APP_DIR"
source venv/bin/activate
pip install --upgrade pip wheel
pip install --upgrade ./apps/api
deactivate

echo "[done] Update complete."