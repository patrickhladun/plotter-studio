from core.config import DATA_DIR
import time

JOB = {
    "proc": None,
    "file": None,
    "progress": None,
    "start_time": None,
    "end_time": None,
    "distance_mm": None,
    "error": None,
}

# Session state for synchronizing dashboard across multiple devices
SESSION_STATE = {
    "selected_file": None,
    "selected_layer": None,
    "last_updated": None,
}
