#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

BASE_ENV_FILE=".env"
DEV_ENV_FILE=".env.development"
PROD_ENV_FILE=".env.production"

# Check if setup has been run
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run 'pnpm setup' first."
    exit 1
fi

if [ ! -d "node_modules" ]; then
    echo "❌ Node modules not found. Run 'pnpm setup' first."
    exit 1
fi

# Create base environment file if it doesn't exist
if [ ! -f "$BASE_ENV_FILE" ]; then
    echo "📝 Creating default $BASE_ENV_FILE file..."
    cat > "$BASE_ENV_FILE" << EOF
PLOTTERSTUDIO_HOME=$PROJECT_ROOT
PLOTTERSTUDIO_HOST=0.0.0.0
PLOTTERSTUDIO_PORT=2222
PLOTTERSTUDIO_DATA_DIR=$PROJECT_ROOT/uploads
EOF
fi

create_env_override() {
    local target_file="$1"
    local label="$2"
    local default_dashboard="$3"
    local default_api="$4"

    if [ -f "$target_file" ]; then
        return
    fi

    cat > "$target_file" << EOF
# $label overrides
DASHBOARD_PORT=$default_dashboard
PLOTTERSTUDIO_PORT=$default_api
EOF
}

create_env_override "$DEV_ENV_FILE" "Development" 2121 2222
create_env_override "$PROD_ENV_FILE" "Production" 3000 3333

# Load environment variables
set -a
source "$BASE_ENV_FILE"
DEV_MODE="${npm_lifecycle_event:-}"
ENV_OVERRIDE_FILE="$PROD_ENV_FILE"
ENV_LABEL="production"
if [ "$DEV_MODE" = "dev" ]; then
    ENV_OVERRIDE_FILE="$DEV_ENV_FILE"
    ENV_LABEL="development"
fi
if [ -f "$ENV_OVERRIDE_FILE" ]; then
    source "$ENV_OVERRIDE_FILE"
fi
set +a

# Default offline behavior depends on script name (dev vs start) unless overridden
if [ -z "${PLOTTERSTUDIO_OFFLINE:-}" ]; then
    if [ "$DEV_MODE" = "dev" ]; then
        export PLOTTERSTUDIO_OFFLINE=1
    else
        export PLOTTERSTUDIO_OFFLINE=0
    fi
fi

LOWER_OFFLINE="$(printf '%s' "${PLOTTERSTUDIO_OFFLINE}" | tr '[:upper:]' '[:lower:]')"
if [[ "$LOWER_OFFLINE" =~ ^(1|true|yes|on)$ ]]; then
    export PLOTTERSTUDIO_OFFLINE=1
    echo "🔌 Offline mode enabled (PLOTTERSTUDIO_OFFLINE=1) — nextdraw commands will be skipped."
else
    export PLOTTERSTUDIO_OFFLINE=0
fi

# Create uploads directory if it doesn't exist
mkdir -p "${PLOTTERSTUDIO_DATA_DIR:-uploads}"

# Get local IP for network access info
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo "🔧 Using ${ENV_LABEL} environment overrides from ${ENV_OVERRIDE_FILE}"
export VITE_API_BASE_URL="http://localhost:${PLOTTERSTUDIO_PORT:-2222}"

echo ""
echo "🚀 Starting Plotter Studio..."
echo ""
echo "  Dashboard: http://localhost:${DASHBOARD_PORT:-2121}"
echo "  API:       http://localhost:${PLOTTERSTUDIO_PORT:-2222}"
echo ""
echo "  Network access:"
echo "  Dashboard: http://${LOCAL_IP}:${DASHBOARD_PORT:-2121}"
echo "  API:       http://${LOCAL_IP}:${PLOTTERSTUDIO_PORT:-2222}"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Trap to clean up background processes
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $API_PID $DASHBOARD_PID 2>/dev/null || true
    wait $API_PID $DASHBOARD_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start API in background
source venv/bin/activate
uvicorn main:app --app-dir apps/api --host "${PLOTTERSTUDIO_HOST:-0.0.0.0}" --port "${PLOTTERSTUDIO_PORT:-2222}" --reload &
API_PID=$!

# Wait a moment for API to start
sleep 2

# Start Dashboard in background
pnpm --filter plotter-studio-dashboard dev &
DASHBOARD_PID=$!

# Wait for both processes
wait $API_PID $DASHBOARD_PID
