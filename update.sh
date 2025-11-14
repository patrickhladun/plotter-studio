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

# --- Update shell profile ---
SHELL_RC="$HOME/.bashrc"
if [ -f "$SHELL_RC" ]; then
  if ! grep -q "PLOTTERSTUDIO_HOME" "$SHELL_RC"; then
    echo "" >> "$SHELL_RC"
    echo "# Plotter Studio environment" >> "$SHELL_RC"
    echo "export PLOTTERSTUDIO_HOME=$APP_DIR" >> "$SHELL_RC"
    echo "[update] Added PLOTTERSTUDIO_HOME to $SHELL_RC"
    echo "[update] Run 'source ~/.bashrc' to apply in current shell"
  fi
fi

echo "[done] Update complete."