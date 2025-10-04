#!/bin/bash
set -euo pipefail

APP_DIR=${APP_DIR:-"$(cd "$(dirname "$0")" && pwd)"}
cd "$APP_DIR"
source venv/bin/activate

ENV_FILE="$APP_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

if [ -x "$APP_DIR/venv/bin/plotterstudio" ]; then
  exec "$APP_DIR/venv/bin/plotterstudio" run "$@"
else
  exec "$APP_DIR/venv/bin/sdraw" run "$@"
fi
