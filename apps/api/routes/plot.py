import time
import logging

from fastapi import APIRouter, Form, HTTPException

from core.nextdraw import (
    _run_command,
    _run_manual,
    _manual_response,
)
from core.state import JOB

router = APIRouter(prefix="/plot", tags=["plot"])
logger = logging.getLogger("plotterstudio.api")

@router.post("")
def plot(command: str = Form(...)):
    """Execute a nextdraw command. The dashboard should build the complete command including all flags."""
    if not command or not command.strip():
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    result = _run_command(command.strip())
    return _manual_response("command executed", result, error_on_failure=False)

@router.post("/cancel")
def cancel():
    if JOB["proc"] and JOB["proc"].poll() is None:
        JOB["proc"].terminate()
        try:
            JOB["proc"].wait(timeout=3)
        except Exception:
            JOB["proc"].kill()
        _run_manual("raise_pen")
        _run_manual("disable_xy")
    JOB["proc"] = None
    JOB["progress"] = None
    JOB["end_time"] = time.time()
    JOB["elapsed_override"] = None
    JOB["error"] = None
    return {"ok": True, "message": "Canceled"}

@router.get("/status")
def status():
    running = JOB["proc"] is not None and JOB["proc"].poll() is None
    progress = JOB.get("progress")
    if not running and progress not in (None, 100.0):
        progress = None
    start_time = JOB.get("start_time")
    end_time = JOB.get("end_time")
    elapsed_override = JOB.get("elapsed_override")
    elapsed = None
    if start_time:
        if running:
            elapsed = time.time() - start_time
        elif end_time:
            elapsed = end_time - start_time
        if elapsed_override is not None:
            elapsed = float(elapsed_override)
    distance_mm = JOB.get("distance_mm")
    return {
        "running": running,
        "file": JOB.get("file"),
        "progress": progress,
        "elapsed_seconds": elapsed,
        "distance_mm": distance_mm,
        "error": JOB.get("error"),
    }

