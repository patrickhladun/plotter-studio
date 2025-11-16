import json
import logging
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import DEFAULT_HOME

router = APIRouter(prefix="/session", tags=["session"])
logger = logging.getLogger("plotterstudio.api")

# Settings directory - store session state JSON file here
SETTINGS_DIR = DEFAULT_HOME / "settings"
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

# Session state file path
SESSION_STATE_FILE = SETTINGS_DIR / "session_state.json"


def _load_session_state() -> dict[str, Any]:
    """Load session state from file, return default if file doesn't exist."""
    if not SESSION_STATE_FILE.exists():
        return {
            "selected_file": None,
            "selected_layer": None,
            "last_updated": None,
        }
    try:
        with SESSION_STATE_FILE.open("r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load session state file %s: %s", SESSION_STATE_FILE, e)
        return {
            "selected_file": None,
            "selected_layer": None,
            "last_updated": None,
        }


def _save_session_state(state: dict[str, Any]) -> None:
    """Save session state to file."""
    try:
        SESSION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with SESSION_STATE_FILE.open("w") as f:
            json.dump(state, f, indent=2)
        logger.debug("Saved session state to %s", SESSION_STATE_FILE)
    except Exception as e:
        logger.error("Failed to save session state file %s: %s", SESSION_STATE_FILE, e)
        raise HTTPException(status_code=500, detail=f"Failed to save session state: {e}")


class SessionStateRequest(BaseModel):
    selected_file: str | None = None
    selected_layer: str | None = None


@router.get("/state")
def get_session_state() -> dict[str, Any]:
    """Get the current session state (for syncing across devices)."""
    state = _load_session_state()
    return {
        "selected_file": state.get("selected_file"),
        "selected_layer": state.get("selected_layer"),
        "last_updated": state.get("last_updated"),
    }


@router.post("/state")
def update_session_state(state: SessionStateRequest) -> dict[str, Any]:
    """Update the session state (for syncing across devices)."""
    current_state = _load_session_state()
    
    # Update only the fields that are provided
    if state.selected_file is not None:
        current_state["selected_file"] = state.selected_file
    if state.selected_layer is not None:
        current_state["selected_layer"] = state.selected_layer
    
    current_state["last_updated"] = time.time()
    
    # Save to file
    _save_session_state(current_state)
    
    logger.info("Session state updated: file=%s, layer=%s", state.selected_file, state.selected_layer)
    return {"ok": True, "message": "Session state updated"}

