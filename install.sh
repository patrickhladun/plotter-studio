#!/bin/bash
set -euo pipefail

APP_DIR=${APP_DIR:-"$HOME/plotter-studio"}
REPO_REF=${REPO_REF:-"main"}
BIN_DIR=${BIN_DIR:-"$HOME/.local/bin"}
ENV_FILE="$APP_DIR/.env"
CERTS_DIR="$APP_DIR/certs"

# -------- Helpers --------
command_exists() { command -v "$1" >/dev/null 2>&1; }
add_env_line() {
  local key="$1" value="$2"
  grep -v "^${key}=" "$ENV_FILE" 2>/dev/null >"${ENV_FILE}.tmp" || true
  mv "${ENV_FILE}.tmp" "$ENV_FILE" 2>/dev/null || true
  echo "${key}=${value}" >>"$ENV_FILE"
}

# -------- System setup --------
echo "[setup] Preparing system..."
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

# -------- Repo setup --------
if [ -d "$APP_DIR/.git" ]; then
  echo "[git] Updating existing repository"
  git -C "$APP_DIR" fetch origin "$REPO_REF" --depth=1
  git -C "$APP_DIR" reset --hard "origin/$REPO_REF"
else
  echo "[git] Cloning repository"
  rm -rf "$APP_DIR"
  git clone --depth 1 --branch "$REPO_REF" https://github.com/patrickhladun/plotter-studio.git "$APP_DIR"
fi

# -------- Python environment --------
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install ./apps/api

# -------- NextDraw API --------
echo "[setup] Installing NextDraw CLI"
NEXTDRAW_URL="https://software-download.bantamtools.com/nd/api/nextdraw_api.zip"
if ! pip install --upgrade "$NEXTDRAW_URL"; then
  echo "[error] Failed to install NextDraw CLI from $NEXTDRAW_URL" >&2
  exit 1
fi
echo "[setup] NextDraw API installed successfully."

# -------- Frontend build --------
pnpm install --filter dashboard --prod=false
pnpm --filter dashboard build

FRONTEND_TARGET="$APP_DIR/apps/api/frontend"
mkdir -p "$FRONTEND_TARGET"
cp -R apps/dashboard/dist/. "$FRONTEND_TARGET/"

# -------- ENV setup --------
touch "$ENV_FILE"
add_env_line "PLOTTERSTUDIO_HOME" "$APP_DIR"
add_env_line "PLOTTERSTUDIO_HOST" "0.0.0.0"
add_env_line "PLOTTERSTUDIO_PORT" "2222"
add_env_line "PLOTTERSTUDIO_FRONTEND_DIST" "$FRONTEND_TARGET"

# -------- Fix CLI launcher --------
CLI_VENV="$APP_DIR/venv/bin/plotterstudio"
if [ -f "$CLI_VENV" ]; then
  echo "[patch] Updating CLI launcher to use apps.api.main"
  sed -i 's|from main import cli|from apps.api.main import cli|' "$CLI_VENV" || true
fi

mkdir -p "$BIN_DIR"
ln -sf "$CLI_VENV" "$BIN_DIR/plotterstudio"

if command_exists sudo; then
  sudo ln -sf "$CLI_VENV" /usr/local/bin/plotterstudio || true
fi

echo "[done] Installation complete."
IP_ADDRESS=$(hostname -I 2>/dev/null | awk '{print $1}' || hostname)
echo "Run with: plotterstudio run"
echo "Then open: http://${IP_ADDRESS}:2222"