#!/bin/bash
set -euo pipefail

APP_DIR=${APP_DIR:-"$HOME/plotter-studio"}
BIN_DIR=${BIN_DIR:-"$HOME/.local/bin"}
CLI_PATH="$BIN_DIR/plotterstudio"
LEGACY_CLI="$BIN_DIR/sdraw"
SYSTEM_CLI="/usr/local/bin/plotterstudio"
LEGACY_SYSTEM_CLI="/usr/local/bin/sdraw"
MARKER="# Added by Plotter Studio installer"
SNIPPET='export PATH="$HOME/.local/bin:$PATH"'
FORCE=${FORCE:-0}

if [ "${1:-}" = "--yes" ] || [ "${1:-}" = "-y" ]; then
  FORCE=1
fi

confirm() {
  local msg=$1
  if [ "$FORCE" = "1" ]; then
    return 0
  fi
  read -r -p "$msg [y/N] " reply
  case "$reply" in
    [yY][eE][sS]|[yY]) return 0 ;;
    *) echo "Aborted."; exit 0 ;;
  esac
}

if [ -d "$APP_DIR" ]; then
  confirm "Remove installation directory $APP_DIR?"
  rm -rf "$APP_DIR"
  echo "[cleanup] Removed $APP_DIR"
else
  echo "[cleanup] No installation directory at $APP_DIR"
fi

for link in "$CLI_PATH" "$LEGACY_CLI"; do
  if [ -L "$link" ] || [ -f "$link" ]; then
    rm -f "$link"
    echo "[cleanup] Removed CLI stub at $link"
  fi
done

for link in "$SYSTEM_CLI" "$LEGACY_SYSTEM_CLI"; do
  if [ -L "$link" ] || [ -f "$link" ]; then
    if command -v sudo >/dev/null 2>&1; then
      sudo rm -f "$link"
      echo "[cleanup] Removed CLI link at $link"
    else
      echo "[warn] CLI link at $link remains (no sudo available). Remove manually if desired."
    fi
  fi
done

SHELL_FILES=(
  "$HOME/.profile"
  "$HOME/.bash_profile"
  "$HOME/.bashrc"
  "$HOME/.zshenv"
  "$HOME/.zprofile"
  "$HOME/.zshrc"
)

for shell_file in "${SHELL_FILES[@]}"; do
  if [ -f "$shell_file" ]; then
    if grep -F "$MARKER" "$shell_file" >/dev/null 2>&1 || grep -F "$SNIPPET" "$shell_file" >/dev/null 2>&1; then
      tmp_file=$(mktemp)
      grep -v -F "$MARKER" "$shell_file" | grep -v -F "$SNIPPET" > "$tmp_file" || true
      mv "$tmp_file" "$shell_file"
      echo "[cleanup] Removed PATH snippet from $shell_file"
    fi
  fi
done

for cmd in plotterstudio sdraw; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "[warn] $cmd still resolves on PATH. Restart your shell or remove additional entries manually."
  else
    echo "[cleanup] $cmd no longer resolves on PATH"
  fi
done

echo "[done] Cleanup complete."
