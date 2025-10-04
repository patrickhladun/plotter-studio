import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional, Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from version import __version__

from routes import svg, plot

logger = logging.getLogger("plotterstudio.api")

ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

app = FastAPI(title="Plotter Studio", version=__version__)

# Shared state for jobs
JOB = {
    "proc": None,
    "file": None,
    "progress": None,
    "start_time": None,
    "end_time": None,
    "distance_mm": None,
    "error": None,
}

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


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "https://plotterstudio.netlify.app",
        "https://plotterstudio.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(svg.router)
app.include_router(plot.router)


@app.get("/status")
def status():
    return {
        "status": "to be coded"
    }


@app.get("/version")
def version():
    return {"version": __version__}


_configure_frontend(app)