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
create_env_override "$PROD_ENV_FILE" "Production" 3131 3333

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

if [ "$DEV_MODE" = "dev" ]; then
    export DASHBOARD_PORT="${DASHBOARD_PORT:-2121}"
    export PLOTTERSTUDIO_PORT="${PLOTTERSTUDIO_PORT:-2222}"
else
    export DASHBOARD_PORT="${DASHBOARD_PORT:-3131}"
    export PLOTTERSTUDIO_PORT="${PLOTTERSTUDIO_PORT:-3333}"
fi

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
# In dev mode, don't set VITE_API_BASE_URL so the dashboard uses the Vite proxy
# In production, set it so the dashboard knows where the API is
if [ "$DEV_MODE" != "dev" ]; then
  export VITE_API_BASE_URL="http://localhost:${PLOTTERSTUDIO_PORT:-3333}"
fi

echo ""
echo "🚀 Starting Plotter Studio..."
echo ""
echo "  Dashboard: http://localhost:${DASHBOARD_PORT}"
echo "  API:       http://localhost:${PLOTTERSTUDIO_PORT}"
echo ""
echo "  Network access:"
echo "  Dashboard: http://${LOCAL_IP}:${DASHBOARD_PORT}"
echo "  API:       http://${LOCAL_IP}:${PLOTTERSTUDIO_PORT}"
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
echo "🔧 Starting API server..."
source venv/bin/activate

# Check if uvicorn is available
if ! command -v uvicorn >/dev/null 2>&1; then
    echo "❌ uvicorn not found. Make sure the virtual environment is activated and dependencies are installed."
    echo "   Run: source venv/bin/activate && pip install ./apps/api"
    exit 1
fi

UVICORN_CMD=(
    uvicorn
    main:app
    --app-dir apps/api
    --host "${PLOTTERSTUDIO_HOST:-0.0.0.0}"
    --port "${PLOTTERSTUDIO_PORT}"
)
if [ "$DEV_MODE" = "dev" ]; then
    UVICORN_CMD+=(
        --reload
        --reload-dir apps/api
        --reload-exclude uploads
        --reload-exclude uploads/*
    )
    if [ -d "rotation" ]; then
        UVICORN_CMD+=(--reload-dir rotation)
    fi
fi

# Start uvicorn and capture output
"${UVICORN_CMD[@]}" > /tmp/plotterstudio-api.log 2>&1 &
API_PID=$!

# Give it a moment to start
sleep 1

# Check if the process is still running
if ! kill -0 $API_PID 2>/dev/null; then
    echo "❌ API server failed to start!"
    echo "📋 API server logs:"
    cat /tmp/plotterstudio-api.log
    exit 1
fi

echo "✅ API server process started (PID: $API_PID)"

# Wait for API to start and verify it's running
echo "⏳ Waiting for API server to start..."
API_READY=false
for i in {1..10}; do
  # Check logs first - faster than curl
  if grep -q "Application startup complete" /tmp/plotterstudio-api.log 2>/dev/null; then
    echo "✅ API server started (found 'Application startup complete' in logs)"
    API_READY=true
    break
  fi
  
  # Also try curl check
  if curl -s --max-time 1 "http://127.0.0.1:${PLOTTERSTUDIO_PORT}/status" > /dev/null 2>&1; then
    echo "✅ API server is running on port ${PLOTTERSTUDIO_PORT}"
    API_READY=true
    break
  fi
  
  # Check if process is still running
  if ! kill -0 $API_PID 2>/dev/null; then
    echo "❌ API server process died!"
    echo "📋 Last 20 lines of API server logs:"
    tail -20 /tmp/plotterstudio-api.log 2>/dev/null || echo "No logs available"
    exit 1
  fi
  
  if [ $i -eq 10 ]; then
    # Final check - if process is running, continue anyway
    if kill -0 $API_PID 2>/dev/null; then
      if grep -q "Uvicorn running" /tmp/plotterstudio-api.log 2>/dev/null; then
        echo "✅ API server appears to be running (found 'Uvicorn running' in logs)"
        API_READY=true
      else
        echo "⚠️  Warning: API server may not be fully ready, but process is running"
        echo "📋 Last 10 lines of API server logs:"
        tail -10 /tmp/plotterstudio-api.log 2>/dev/null || echo "No logs available"
        echo "Continuing anyway..."
      fi
    fi
  else
    sleep 0.5
  fi
done

# Start Dashboard in background
pnpm --filter plotter-studio-dashboard dev &
DASHBOARD_PID=$!

# Wait for both processes
wait $API_PID $DASHBOARD_PID
