import time
import logging
import shlex
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException

from core.nextdraw import (
    _run_command,
    _manual_response,
)
from core.state import JOB
from core.config import DATA_DIR
from core.utils import _sanitize_filename

router = APIRouter(prefix="/plot", tags=["plot"])
logger = logging.getLogger("plotterstudio.api")

@router.post("")
def plot(command: str = Form(...)):
    """Execute a nextdraw command. The dashboard should build the complete command including all flags."""
    if not command or not command.strip():
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    command_str = command.strip()
    logger.info("API received command: %s", command_str)
    
    # Parse command to resolve filename to full path
    parts = shlex.split(command_str)
    if len(parts) > 1:
        # Look for the first argument that looks like a filename (after 'nextdraw' and flags)
        # Flags start with '-' or '--', so skip those
        for i, part in enumerate(parts):
            if i == 0:
                continue  # Skip 'nextdraw'
            if part.startswith('-'):
                continue  # Skip flags
            # This might be a filename - check if it exists in DATA_DIR
            safe_name = _sanitize_filename(part)
            full_path = DATA_DIR / safe_name
            if full_path.exists() and full_path.is_file():
                # Replace filename with full path
                parts[i] = str(full_path)
                logger.info("Resolved filename '%s' to full path: %s", part, full_path)
                break
        # Reconstruct command with resolved path
        command_str = ' '.join(shlex.quote(str(p)) for p in parts)
        logger.info("Command with resolved path: %s", command_str)
    
    result = _run_command(command_str)
    response = _manual_response("command executed", result, error_on_failure=False)
    # Also include the original command string for debugging
    response["original_command"] = command_str
    return response

@router.post("/cancel")
def cancel():
    if JOB["proc"] and JOB["proc"].poll() is None:
        JOB["proc"].terminate()
        try:
            JOB["proc"].wait(timeout=3)
        except Exception:
            JOB["proc"].kill()
        # Dashboard should handle raising pen and disabling motors if needed
        # The cancel endpoint just stops the running process
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

