import logging
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ============================================================
# Dynamic Path Fix — must be BEFORE any local imports
# ============================================================
CURRENT_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURRENT_DIR.parent

# Add both /api and /api/parent to sys.path so routes/core are visible
for path in [CURRENT_DIR, PARENT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# ============================================================
# Now safe to import local modules
# ============================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from version import __version__
from core.state import DATA_DIR
from routes import svg, plot

# ============================================================
# Logging Setup
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("plotterstudio.api")


# ============================================================
# SVG Namespace & FastAPI App Setup
# ============================================================
ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

app = FastAPI(title="Plotter Studio", version=__version__)

# ============================================================


FRONTEND_DIST = Path(
    os.getenv("PLOTTERSTUDIO_FRONTEND_DIST")
    or os.getenv("SYNTHDRAW_FRONTEND_DIST")
    or Path(__file__).resolve().parent / "frontend"
)

DEFAULT_HOME = Path(
    os.getenv("PLOTTERSTUDIO_HOME")
    or os.getenv("SYNTHDRAW_HOME")
    or Path.home() / "plotter-studio"
)

DATA_DIR = Path(
    os.getenv("PLOTTERSTUDIO_DATA_DIR")
    or os.getenv("SYNTHDRAW_DATA_DIR")
    or DEFAULT_HOME / "uploads"
)
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _configure_frontend(app: FastAPI) -> None:
    """Serve built dashboard files if present."""
    if not FRONTEND_DIST.exists():
        logger.warning("Frontend bundle directory not found at %s", FRONTEND_DIST)
        return

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        logger.warning("Frontend bundle missing index.html at %s", index_file)
        return

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_file)


# ============================================================
# CORS + Routes
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:2121"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(svg.router)
app.include_router(plot.router)


# ============================================================
# Core Endpoints
# ============================================================
@app.get("/status")
def status():
    logger.info("Status endpoint called.")
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": __version__}


# ============================================================
# Frontend & Init Logging
# ============================================================
_configure_frontend(app)

logger.info("Plotter Studio API initialized.")
logger.info(f"Frontend path: {FRONTEND_DIST}")
logger.info(f"Data directory: {DATA_DIR}")