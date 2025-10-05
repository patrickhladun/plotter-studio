#!/bin/bash
set -euo pipefail

APP_DIR=${APP_DIR:-"$HOME/plotter-studio"}
REPO_REF=${REPO_REF:-"main"}
BIN_DIR=${BIN_DIR:-"$HOME/.local/bin"}
ENV_FILE="$APP_DIR/.env"

command_exists() { command -v "$1" >/dev/null 2>&1; }

echo "[setup] Installing Plotter Studio into $APP_DIR"

# --- Dependencies ---
if command_exists apt-get; then
  sudo apt-get update -y
  sudo apt-get install -y python3 python3-venv python3-pip git curl build-essential
fi

if ! command_exists node || [ "$(node -v | cut -d. -f1 | tr -d 'v')" -lt 18 ]; then
  echo "[setup] Installing Node.js v20"
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

if ! command_exists pnpm; then
  echo "[setup] Installing pnpm"
  sudo npm install -g pnpm@8
fi

# --- Repo ---
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch origin "$REPO_REF" --depth=1
  git -C "$APP_DIR" reset --hard "origin/$REPO_REF"
else
  rm -rf "$APP_DIR"
  git clone --depth 1 --branch "$REPO_REF" https://github.com/patrickhladun/plotter-studio.git "$APP_DIR"
fi

cd "$APP_DIR"

# --- Python setup ---
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install ./apps/api

# --- NextDraw API ---
echo "[setup] Installing NextDraw CLI"
if ! pip install --upgrade https://software-download.bantamtools.com/nd/api/nextdraw_api.zip; then
  echo "[warn] Could not install NextDraw API, skipping"
fi

# --- Build dashboard ---
pnpm install --filter dashboard --prod=false
pnpm --filter dashboard build

FRONTEND_TARGET="$APP_DIR/apps/api/frontend"
mkdir -p "$FRONTEND_TARGET"
cp -R apps/dashboard/dist/. "$FRONTEND_TARGET/"

# --- Environment ---
touch "$ENV_FILE"
echo "PLOTTERSTUDIO_HOME=$APP_DIR" > "$ENV_FILE"
echo "PLOTTERSTUDIO_HOST=0.0.0.0" >> "$ENV_FILE"
echo "PLOTTERSTUDIO_PORT=2222" >> "$ENV_FILE"
echo "PLOTTERSTUDIO_FRONTEND_DIST=$FRONTEND_TARGET" >> "$ENV_FILE"

# --- Patch CLI launcher ---
CLI_FILE="$APP_DIR/venv/bin/plotterstudio"
if [ -f "$CLI_FILE" ]; then
  echo "[patch] Updating CLI launcher to use plotterstudio.main"
  sed -i 's|from main import cli|from plotterstudio.main import cli|' "$CLI_FILE" || true
fi

# --- Symlink to user bin ---
mkdir -p "$BIN_DIR"
ln -sf "$CLI_FILE" "$BIN_DIR/plotterstudio"

if command_exists sudo; then
  sudo ln -sf "$CLI_FILE" /usr/local/bin/plotterstudio || true
fi

deactivate

IP_ADDRESS=$(hostname -I 2>/dev/null | awk '{print $1}' || hostname)
echo "[done] Installation complete."
echo "Run: plotterstudio run"
echo "Open: http://${IP_ADDRESS}:2222"