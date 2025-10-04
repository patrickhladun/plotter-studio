#!/bin/bash
set -euo pipefail

APP_DIR=${APP_DIR:-"$HOME/plotter-studio"}
ENV_FILE="$APP_DIR/.env"

discover_axicli() {
  if [ -n "${PLOTTERSTUDIO_AXICLI:-}" ]; then
    printf '%s\n' "$PLOTTERSTUDIO_AXICLI"
    return 0
  fi
  if [ -n "${SYNTHDRAW_AXICLI:-}" ]; then
    printf '%s\n' "$SYNTHDRAW_AXICLI"
    return 0
  fi

  if command -v axicli >/dev/null 2>&1; then
    command -v axicli
    return 0
  fi

  if command -v pyenv >/dev/null 2>&1; then
    local pyroot
    pyroot=$(pyenv root 2>/dev/null || true)
    if [ -n "$pyroot" ] && [ -d "$pyroot/versions" ]; then
      local candidate
      while IFS= read -r -d '' candidate; do
        printf '%s\n' "$candidate"
        return 0
      done < <(find "$pyroot/versions" -type f -path '*/bin/axicli' -print0 2>/dev/null)
    fi
  fi

  printf '%s\n' "axicli"
  return 1
}

set_env_value() {
  local key=$1
  local value=$2
  local file=$3
  local tmp

  tmp=$(mktemp)
  if [ -f "$file" ]; then
    grep -v "^${key}=" "$file" | grep -v '^SYNTHDRAW_API_AXICLI=' | grep -v '^PLOTTERSTUDIO_API_AXICLI=' > "$tmp" || true
  fi
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
  mv "$tmp" "$file"
  chmod 600 "$file"
}

if [ ! -d "$APP_DIR" ]; then
  echo "Plotter Studio is not installed in $APP_DIR"
  exit 1
fi

echo "[update] Fetching latest version"

git -C "$APP_DIR" pull --ff-only

cd "$APP_DIR"
source venv/bin/activate
pip install --upgrade pip wheel
pip install --upgrade .
pip install --upgrade axidraw

axicli_path=$(discover_axicli)
if [ "$axicli_path" = "axicli" ]; then
  echo "[warn] Could not auto-detect axicli executable; leaving PATH-based fallback"
else
  echo "[update] Setting PLOTTERSTUDIO_AXICLI to $axicli_path"
fi
set_env_value "PLOTTERSTUDIO_AXICLI" "$axicli_path" "$ENV_FILE"
set_env_value "SYNTHDRAW_AXICLI" "$axicli_path" "$ENV_FILE"

echo "[done] Update complete"
