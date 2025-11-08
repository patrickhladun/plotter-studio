#!/bin/bash
set -euo pipefail

APP_DIR=${APP_DIR:-"$HOME/plotter-studio"}
BIN_DIR=${BIN_DIR:-"$HOME/.local/bin"}
CLI_PATH="$BIN_DIR/plotterstudio"
SYSTEM_CLI="/usr/local/bin/plotterstudio"

echo "[cleanup] Removing installation..."
rm -rf "$APP_DIR" "$CLI_PATH"

if command -v sudo >/dev/null 2>&1; then
  sudo rm -f "$SYSTEM_CLI" || true
fi

echo "[cleanup] Done. Restart your shell to refresh PATH."