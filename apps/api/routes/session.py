import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.state import SESSION_STATE

router = APIRouter(prefix="/session", tags=["session"])
logger = logging.getLogger("plotterstudio.api")


class SessionStateRequest(BaseModel):
    selected_file: str | None = None
    selected_layer: str | None = None


@router.get("/state")
def get_session_state() -> dict[str, Any]:
    """Get the current session state (for syncing across devices)."""
    return {
        "selected_file": SESSION_STATE.get("selected_file"),
        "selected_layer": SESSION_STATE.get("selected_layer"),
        "last_updated": SESSION_STATE.get("last_updated"),
    }


@router.post("/state")
def update_session_state(state: SessionStateRequest) -> dict[str, str]:
    """Update the session state (for syncing across devices)."""
    if state.selected_file is not None:
        SESSION_STATE["selected_file"] = state.selected_file
    if state.selected_layer is not None:
        SESSION_STATE["selected_layer"] = state.selected_layer
    
    SESSION_STATE["last_updated"] = time.time()
    logger.info("Session state updated: file=%s, layer=%s", state.selected_file, state.selected_layer)
    return {"ok": True, "message": "Session state updated"}

