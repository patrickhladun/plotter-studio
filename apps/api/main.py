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

from version import __version__
from apps.api.core.state import DATA_DIR
from apps.api.routes import svg, plot

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


# ============================================================
# CORS + Routes
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:2121",  # Vite dev server
        "http://localhost:5173",  # Alternative Vite port
        "http://127.0.0.1:2121",
        "http://127.0.0.1:5173",
    ],
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
# Init Logging
# ============================================================
logger.info("Plotter Studio API initialized.")
logger.info(f"Data directory: {DATA_DIR}")