import logging
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
from core.config import DATA_DIR, cors_origins, OFFLINE_MODE, dashboard_origin_regex
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
# CORS + Routes
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_origin_regex=dashboard_origin_regex(),
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
if OFFLINE_MODE:
    logger.warning("Offline mode enabled - nextdraw commands will be skipped.")
