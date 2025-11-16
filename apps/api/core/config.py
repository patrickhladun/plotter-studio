import os
from pathlib import Path
import re
from typing import Iterable, Sequence, Optional


def _first_existing_path(env_names: Iterable[str], fallback: Path) -> Path:
    for name in env_names:
        value = os.getenv(name)
        if value:
            return Path(value).expanduser()
    return fallback


def _env_flag(name: str, default: bool = False) -> bool:
    """Interpret boolean-ish environment variables."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEFAULT_HOME = _first_existing_path(
    ("PLOTTERSTUDIO_HOME", "SYNTHDRAW_HOME"),
    Path.home() / "plotter-studio",
)

DATA_DIR = _first_existing_path(
    ("PLOTTERSTUDIO_DATA_DIR", "SYNTHDRAW_DATA_DIR"),
    DEFAULT_HOME / "uploads",
)
DATA_DIR.mkdir(parents=True, exist_ok=True)

OFFLINE_MODE = _env_flag("PLOTTERSTUDIO_OFFLINE")


DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:2121",
    "http://localhost:5173",
    "http://127.0.0.1:2121",
    "http://127.0.0.1:5173",
    "http://localhost:3131",
    "http://127.0.0.1:3131",
    # Production dashboard port
    "http://192.168.1.37:3131",
)


def cors_origins(extra: Sequence[str] | None = None) -> list[str]:
    """Return default CORS origins merged with optional overrides."""
    merged = list(DEFAULT_CORS_ORIGINS)
    if extra:
        merged.extend(value for value in extra if value not in merged)
    return merged


def dashboard_origin_regex() -> Optional[str]:
    """Allow dashboard to access API from any host when using its configured port.
    
    Supports both development (2121, 5173) and production (3131) ports.
    """
    port = os.getenv("DASHBOARD_PORT")
    if not port:
        # If no port specified, allow common dev and production ports
        return r"^https?://[^/]+:(2121|5173|3131)$"
    port = port.strip()
    if not port:
        return r"^https?://[^/]+:(2121|5173|3131)$"
    escaped = re.escape(port)
    return rf"^https?://[^/]+:{escaped}$"
