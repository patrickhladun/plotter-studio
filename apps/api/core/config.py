import os
from pathlib import Path
from typing import Iterable, Sequence


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
)


def cors_origins(extra: Sequence[str] | None = None) -> list[str]:
    """Return default CORS origins merged with optional overrides."""
    merged = list(DEFAULT_CORS_ORIGINS)
    if extra:
        merged.extend(value for value in extra if value not in merged)
    return merged
