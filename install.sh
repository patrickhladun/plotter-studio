#!/bin/bash
set -euo pipefail

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

add_env_line() {
  local key="$1"
  local value="$2"
  if [ -f "$ENV_FILE" ]; then
    grep -v "^${key}=" "$ENV_FILE" >"${ENV_FILE}.tmp" || true
    mv "${ENV_FILE}.tmp" "$ENV_FILE"
  fi
  echo "${key}=${value}" >>"$ENV_FILE"
}

ensure_packages() {
  if command_exists apt-get; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip git curl build-essential
  fi
}

install_node() {
  local required_major=18
  if command_exists node; then
    local current_major
    current_major=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$current_major" -ge "$required_major" ]; then
      return
    fi
  fi

  if ! command_exists curl; then
    echo "[error] curl not available; install curl and rerun" >&2
    exit 1
  fi

  echo "[setup] Installing Node.js (v20.x) via NodeSource"
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
}

install_pnpm() {
  if command_exists pnpm; then
    return
  fi

  if command_exists corepack; then
    echo "[setup] Enabling pnpm via corepack"
    corepack enable pnpm || true
    if command_exists pnpm; then
      return
    fi
  fi

  echo "[setup] Installing pnpm globally"
  sudo npm install -g pnpm@8
}

install_nextdraw_cli() {
  echo "[setup] Installing Nextdraw CLI"
  local nextdraw_url="https://software-download.bantamtools.com/nd/api/nextdraw_api.zip"

  if pip install --upgrade "$nextdraw_url"; then
    echo "[setup] Nextdraw API installed"
  else
    echo "[error] Failed to install Nextdraw CLI from $nextdraw_url" >&2
    return 1
  fi
}

APP_DIR=${APP_DIR:-"$HOME/plotter-studio"}
REPO_URL=${REPO_URL:-"https://github.com/patrickhladun/plotter-studio.git"}
REPO_REF=${REPO_REF:-"main"}
BIN_DIR=${BIN_DIR:-"$HOME/.local/bin"}
ENV_FILE="$APP_DIR/.env"
CERTS_DIR="$APP_DIR/certs"
TLS_ENABLED=${PLOTTERSTUDIO_ENABLE_TLS:-${SYNTHDRAW_ENABLE_TLS:-0}}

echo "[setup] Installing Plotter Studio into $APP_DIR"

ensure_packages
install_node
install_pnpm

if [ -d "$APP_DIR/.git" ]; then
  echo "[setup] Repository already present; pulling latest changes"
  git -C "$APP_DIR" fetch origin "$REPO_REF"
  git -C "$APP_DIR" checkout "$REPO_REF"
  git -C "$APP_DIR" reset --hard "origin/$REPO_REF"
else
  echo "[setup] Cloning repository from $REPO_URL"
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
  git -C "$APP_DIR" checkout "$REPO_REF"
fi

cd "$APP_DIR"

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install ./apps/api
install_nextdraw_cli

NEXTDRAW_PATH="$APP_DIR/venv/bin/nextdraw"
if [ ! -x "$NEXTDRAW_PATH" ]; then
  echo "[error] nextdraw not found in venv after install!" >&2
  exit 1
fi

touch "$ENV_FILE"
add_env_line "PLOTTERSTUDIO_NEXTDRAW" "$NEXTDRAW_PATH"
add_env_line "PLOTTERSTUDIO_HOME" "$APP_DIR"
add_env_line "PLOTTERSTUDIO_ENV_FILE" "$ENV_FILE"
add_env_line "PLOTTERSTUDIO_HOST" "0.0.0.0"
add_env_line "PLOTTERSTUDIO_PORT" "2222"
add_env_line "SYNTHDRAW_AXICLI" "$NEXTDRAW_PATH"
add_env_line "SYNTHDRAW_HOME" "$APP_DIR"
add_env_line "SYNTHDRAW_ENV_FILE" "$ENV_FILE"
add_env_line "SYNTHDRAW_HOST" "0.0.0.0"
add_env_line "SYNTHDRAW_PORT" "2222"

pnpm install --filter dashboard --prod=false
pnpm --filter dashboard build

FRONTEND_TARGET="$APP_DIR/apps/api/frontend"
rm -rf "$FRONTEND_TARGET"
mkdir -p "$FRONTEND_TARGET"
cp -R apps/dashboard/dist/. "$FRONTEND_TARGET/"
add_env_line "PLOTTERSTUDIO_FRONTEND_DIST" "$FRONTEND_TARGET"
add_env_line "SYNTHDRAW_FRONTEND_DIST" "$FRONTEND_TARGET"

# also stage the bundle inside the installed package so the default path works
PACKAGE_FRONTEND_DIR=$(python - <<'PY'
import importlib.util
from pathlib import Path

spec = importlib.util.find_spec("main")
if not spec or not spec.origin:
    print()
else:
    package_dir = Path(spec.origin).resolve().parent
    print(package_dir / "frontend")
PY
)

if [ -n "$PACKAGE_FRONTEND_DIR" ]; then
  echo "[setup] Writing dashboard bundle to $PACKAGE_FRONTEND_DIR"
  rm -rf "$PACKAGE_FRONTEND_DIR"
  mkdir -p "$PACKAGE_FRONTEND_DIR"
  cp -R apps/dashboard/dist/. "$PACKAGE_FRONTEND_DIR/"
else
  echo "[warn] Unable to resolve installed package location for frontend copy"
fi

if [ "$TLS_ENABLED" = "1" ]; then
  if ! command_exists mkcert; then
    if command_exists apt-get; then
      echo "[tls] Installing mkcert and dependencies"
      sudo apt-get install -y mkcert libnss3-tools
    else
      echo "[warn] mkcert not found and package manager unavailable; skipping TLS"
      TLS_ENABLED=0
    fi
  fi

  if [ "$TLS_ENABLED" = "1" ]; then
    mkdir -p "$CERTS_DIR"
    default_cn=${PLOTTERSTUDIO_TLS_CN:-${SYNTHDRAW_TLS_CN:-$(hostname -I 2>/dev/null | awk '{print $1}')}}
    [ -z "$default_cn" ] && default_cn=$(hostname -f 2>/dev/null || hostname)
    cn=${PLOTTERSTUDIO_TLS_CN:-${SYNTHDRAW_TLS_CN:-$default_cn}}
    echo "[tls] Using Common Name: $cn"
    mkcert -install
    cert_file="$CERTS_DIR/${cn}.pem"
    key_file="$CERTS_DIR/${cn}-key.pem"
    if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
      echo "[tls] Generating new certificate"
      mkcert -cert-file "$cert_file" -key-file "$key_file" "$cn" localhost 127.0.0.1 ::1
    else
      echo "[tls] Reusing existing certificate files"
    fi
    add_env_line "PLOTTERSTUDIO_SSL_CERTFILE" "$cert_file"
    add_env_line "PLOTTERSTUDIO_SSL_KEYFILE" "$key_file"
    add_env_line "SYNTHDRAW_SSL_CERTFILE" "$cert_file"
    add_env_line "SYNTHDRAW_SSL_KEYFILE" "$key_file"
  fi
else
  echo "[tls] TLS generation disabled (PLOTTERSTUDIO_ENABLE_TLS=$TLS_ENABLED)"
fi

deactivate

mkdir -p "$BIN_DIR"
ln -sf "$APP_DIR/venv/bin/plotterstudio" "$BIN_DIR/plotterstudio"
ln -sf "$APP_DIR/venv/bin/plotterstudio" "$BIN_DIR/sdraw"  # legacy shim
if command_exists sudo; then
  sudo ln -sf "$APP_DIR/venv/bin/plotterstudio" /usr/local/bin/plotterstudio || true
  sudo ln -sf "$APP_DIR/venv/bin/plotterstudio" /usr/local/bin/sdraw || true
fi

if ! command_exists plotterstudio; then
  PATH_SNIPPET='export PATH="$HOME/.local/bin:$PATH"'
  if ! grep -qs "$PATH_SNIPPET" "$HOME/.profile" 2>/dev/null; then
    echo "$PATH_SNIPPET" >>"$HOME/.profile"
  fi
  echo "[note] Restart your shell or run 'source ~/.profile' to use plotterstudio"
fi

IP_ADDRESS=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$IP_ADDRESS" ]; then
  IP_ADDRESS="$(hostname)"
fi

echo "[done] Installation complete."
echo "Start the combined API + dashboard with:"
echo "  plotterstudio run"
echo "  (legacy) sdraw run"
echo "Then open: http://${IP_ADDRESS}:2222"
