import re
from pathlib import Path
from fastapi import HTTPException

def _sanitize_filename(name: str) -> str:
    """Sanitize and validate an uploaded SVG filename."""
    if not name:
        raise HTTPException(status_code=400, detail="Filename is required")
    candidate = Path(name).name
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", candidate)
    if not safe.lower().endswith(".svg"):
        raise HTTPException(status_code=400, detail="Only .svg files are supported")
    return safe