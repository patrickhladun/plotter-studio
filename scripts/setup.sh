#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Setting up Plotter Studio..."

# Check for Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

# Check for pnpm
if ! command -v pnpm >/dev/null 2>&1; then
    echo "❌ pnpm not found. Please install pnpm: npm install -g pnpm"
    exit 1
fi

# Create Python virtual environment
echo "📦 Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv and install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip wheel
pip install ./apps/api

# Install NextDraw API
echo "📦 Installing NextDraw API..."
if ! pip install --upgrade https://software-download.bantamtools.com/nd/api/nextdraw_api.zip; then
    echo "⚠️  Could not install NextDraw API (optional)"
fi

deactivate

# Install Node dependencies
echo "📦 Installing Node dependencies..."
pnpm install

# Create .env file with defaults
echo "📝 Creating .env file..."
cat > .env << 'EOF'
# Plotter Studio Configuration
PLOTTERSTUDIO_HOME=$PROJECT_ROOT
PLOTTERSTUDIO_HOST=0.0.0.0
PLOTTERSTUDIO_PORT=2222
PLOTTERSTUDIO_DATA_DIR=$PROJECT_ROOT/uploads

# Dashboard Configuration
DASHBOARD_PORT=2121
EOF

# Replace $PROJECT_ROOT with actual path
sed -i "s|\$PROJECT_ROOT|$PROJECT_ROOT|g" .env

# Create uploads directory
mkdir -p uploads

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start Plotter Studio:"
echo "  pnpm start"
echo ""
echo "The application will be available at:"
echo "  Dashboard: http://localhost:2121"
echo "  API: http://localhost:2222"
echo ""
