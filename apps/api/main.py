import logging
import os, sys
import xml.etree.ElementTree as ET
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from version import __version__
from apps.api.routes import svg, plot
from core.state import DATA_DIR


# Detect and adjust path dynamically for both dev and installed runs
CURRENT_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURRENT_DIR.parent
PROJECT_ROOT = PARENT_DIR.parent

# In dev: /plotter-studio/software/apps/api/
# In prod: /plotter-studio/apps/api/ (after install)
# Ensure both `core` and `routes` are importable
if (CURRENT_DIR / "core").exists():
    sys.path.insert(0, str(CURRENT_DIR))
elif (PARENT_DIR / "core").exists():
    sys.path.insert(0, str(PARENT_DIR))
else:
    sys.path.insert(0, str(PROJECT_ROOT))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("plotterstudio.api")

# ============================================================
# SVG Namespace & App Setup
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:2121"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(svg.router)
app.include_router(plot.router)


@app.get("/status")
def status():
    logger.info("Status endpoint called.")
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": __version__}


_configure_frontend(app)

logger.info("Plotter Studio API initialized.")
logger.info(f"Frontend path: {FRONTEND_DIST}")
logger.info(f"Data directory: {DATA_DIR}")