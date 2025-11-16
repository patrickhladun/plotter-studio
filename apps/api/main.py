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
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time

from version import __version__
from core.config import DATA_DIR, cors_origins, OFFLINE_MODE, dashboard_origin_regex
from routes import svg, plot, config, session, settings

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
# Request Logging Middleware
# ============================================================
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        logger.info("→ %s %s", request.method, request.url.path)
        logger.info("  Headers: %s", dict(request.headers))
        if request.url.query:
            logger.info("  Query: %s", request.url.query)
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info("← %s %s - %d (%.3fs)", request.method, request.url.path, response.status_code, process_time)
            return response
        except Exception as exc:
            process_time = time.time() - start_time
            logger.exception("✗ %s %s - ERROR after %.3fs: %s", request.method, request.url.path, process_time, type(exc).__name__)
            raise

app.add_middleware(RequestLoggingMiddleware)

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
app.include_router(config.router)
app.include_router(session.router)
app.include_router(settings.router)


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


@app.get("/debug/logs")
def get_recent_logs(lines: int = 50):
    """Get recent log entries from the API log file."""
    log_file = Path("/tmp/plotterstudio-api.log")
    if not log_file.exists():
        return {"error": "Log file not found", "path": str(log_file)}
    
    try:
        with log_file.open("r") as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return {
                "total_lines": len(all_lines),
                "returned_lines": len(recent),
                "logs": recent
            }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Init Logging
# ============================================================
logger.info("Plotter Studio API initialized.")
logger.info(f"Data directory: {DATA_DIR}")
if OFFLINE_MODE:
    logger.warning("Offline mode enabled - nextdraw commands will be skipped.")
