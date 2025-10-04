import os
import tempfile
import time
import logging
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile

from core.nextdraw import (
    _run_manual,
    _run_utility,
    _start_plot_from_path,
    _manual_response,
)
from core.state import JOB

router = APIRouter(prefix="/plot", tags=["plot"])
logger = logging.getLogger("plotterstudio.api")

@router.post("")
async def plot(
    file: UploadFile,
    page: str = Form("a5"),
    s_down: int = Form(30),
    s_up: int = Form(70),
    p_down: int = Form(40),
    p_up: int = Form(70),
    handling: int = Form(1),
    speed: int = Form(70),
    brushless: bool = Form(False),
):
    fd, temp_path = tempfile.mkstemp(suffix=".svg")
    temp_file = Path(temp_path)
    try:
        with os.fdopen(fd, "wb") as handle:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

        if temp_file.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        return _start_plot_from_path(
            temp_file,
            page,
            s_down,
            s_up,
            p_down,
            p_up,
            handling,
            speed,
            brushless,
            original_name=file.filename,
        )
    finally:
        try:
            temp_file.unlink()
        except FileNotFoundError:
            pass

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

@router.post("/enable_motors")
def enable_motors():
    result = _run_utility("enable_xy")
    return _manual_response("motors enabled", result, error_on_failure=False)

@router.post("/disable_motors")
def disable_motors():
    result = _run_utility("disable_xy")
    return _manual_response("motors disabled", result, error_on_failure=False)

@router.post("/pen/toggle")
def pen_toggle():
    command = ["toggle"]
    result = _run_utility(*command)
    return _manual_response("pen toggled", result, error_on_failure=False)