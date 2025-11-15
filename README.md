# Plotter Studio

A modern web-based interface for controlling NextDraw/AxiDraw pen plotters. Upload SVG files, configure plot settings, and control your plotter from any device on your network.

## Features

- 🎨 **SVG File Management** - Upload, preview, rotate, rename, and delete SVG artwork
- 🖊️ **Real-time Plotter Control** - Start/stop plotting with live progress monitoring
- ⚙️ **Configurable Settings** - Paper sizes (A3/A4/A5/A6), speed, pen pressure
- 📊 **Plot Estimation** - Time and distance estimates before plotting
- 🔧 **Manual Controls** - Direct control over motors and pen position
- 🌐 **Network Accessible** - Access from any device on your local network

## Quick Start

### Prerequisites

- **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **pnpm** - Install with: `npm install -g pnpm`

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/patrickhladun/plotter-studio.git
   cd plotter-studio
   ```

2. **Install dependencies**
   ```bash
   pnpm install
   bash scripts/setup.sh
   ```

3. **Start the application**
   ```bash
   pnpm start
   ```

4. **Open in your browser**
   - **Dashboard**: http://localhost:2121
   - **API**: http://localhost:2222

### Network Access

Access from other devices on your network:
```bash
# Find your device's IP address
hostname -I

# Access from another device
http://<device-ip>:2121
```

## Project Structure

```
plotter-studio/
├── apps/
│   ├── api/              # FastAPI backend
│   │   ├── core/         # Core logic and state management
│   │   ├── routes/       # API endpoints (svg, plot)
│   │   └── main.py       # API entry point
│   └── dashboard/        # Svelte frontend
│       └── src/
│           ├── components/
│           └── lib/
├── scripts/              # Setup and startup scripts
├── uploads/              # SVG file storage
├── .env                  # Shared configuration (auto-generated)
├── .env.development      # Dev-only overrides (ports, etc.)
└── .env.production       # Production overrides
```

## Development

### Available Scripts

```bash
pnpm start            # Start both API and dashboard
pnpm dev              # Same as start (with hot reload)
pnpm dev:api          # Start only the API
pnpm dev:dashboard    # Start only the dashboard
pnpm build:dashboard  # Build dashboard for production
```

### Configuration

Edit `.env` for shared settings (API home, data dir, etc.), and use the override files to set different ports per mode:

```bash
# .env (shared defaults)
PLOTTERSTUDIO_HOST=0.0.0.0
PLOTTERSTUDIO_DATA_DIR=./uploads

# .env.development (used by pnpm dev)
DASHBOARD_PORT=2121
PLOTTERSTUDIO_PORT=2222

# .env.production (used by pnpm start)
DASHBOARD_PORT=3000
PLOTTERSTUDIO_PORT=3333
```

## API Endpoints

### SVG Management
- `GET /svg/files` - List all uploaded SVG files
- `POST /svg/upload` - Upload a new SVG file
- `GET /svg/preview/{filename}` - Get SVG preview with transformations
- `DELETE /svg/files/{filename}` - Delete an SVG file

### Plotting
- `POST /plot/start` - Start plotting a file
- `POST /plot/cancel` - Cancel current plot
- `GET /plot/status` - Get current plotting status and progress
- `POST /plot/enable_motors` - Enable stepper motors
- `POST /plot/disable_motors` - Disable stepper motors

### Pen Control
- `POST /plot/pen/up` - Raise the pen
- `POST /plot/pen/down` - Lower the pen

## Hardware Requirements

- **NextDraw or AxiDraw plotter**
- **Raspberry Pi** (recommended) or any Linux/macOS/Windows computer
- **USB connection** to the plotter

## Technology Stack

- **Backend**: FastAPI (Python), NextDraw API, uvicorn
- **Frontend**: Svelte, Vite, TailwindCSS, TypeScript
- **Plotter**: NextDraw/AxiDraw compatible devices

## Troubleshooting

### Port already in use
```bash
# Find and kill process using the port
lsof -i :2222
kill <PID>
```

### Python virtual environment issues
```bash
# Remove and recreate
rm -rf venv
bash scripts/setup.sh
```

### Dashboard can't connect to API
- Verify both services are running
- Check CORS settings in `apps/api/main.py`
- Ensure firewall isn't blocking the ports

### NextDraw API not found
The setup script attempts to install it automatically. If it fails:
```bash
source venv/bin/activate
pip install https://software-download.bantamtools.com/nd/api/nextdraw_api.zip
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## Architecture

- **Monorepo** with separate API and dashboard workspaces
- **API and dashboard run independently** - API on port 2222, dashboard on port 2121
- **CORS enabled** for cross-origin requests during development
- **Real-time updates** via polling (status endpoint)

## Acknowledgments

- Built on the [NextDraw API](https://bantamtools.com/nextdraw)
- Inspired by the AxiDraw ecosystem
- Designed for artists, designers, and hobbyists creating physical art with pen plotters
