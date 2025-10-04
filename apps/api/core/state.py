from pathlib import Path
import os

JOB = {
    "proc": None,
    "file": None,
    "progress": None,
    "start_time": None,
    "end_time": None,
    "distance_mm": None,
    "error": None,
}

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