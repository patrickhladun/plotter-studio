#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Check if setup has been run
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run 'pnpm setup' first."
    exit 1
fi

if [ ! -d "node_modules" ]; then
    echo "❌ Node modules not found. Run 'pnpm setup' first."
    exit 1
fi

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating default .env file..."
    cat > .env << EOF
PLOTTERSTUDIO_HOME=$PROJECT_ROOT
PLOTTERSTUDIO_HOST=0.0.0.0
PLOTTERSTUDIO_PORT=2222
PLOTTERSTUDIO_DATA_DIR=$PROJECT_ROOT/uploads
DASHBOARD_PORT=2121
EOF
fi

# Load environment variables
set -a
source .env
set +a

# Create uploads directory if it doesn't exist
mkdir -p "${PLOTTERSTUDIO_DATA_DIR:-uploads}"

# Get local IP for network access info
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

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
