from pathlib import Path
from typing import Any

from fastapi import APIRouter, UploadFile, HTTPException, Response, Query
from fastapi.responses import FileResponse

from core.utils import _sanitize_filename
from core.files import _file_metadata, _unique_filename
from core.schemas import RotateRequest, RenameRequest, PlotRequest
from core.nextdraw import _preview_via_nextdraw, _estimate_distance_mm, _start_plot_from_path
from core.config import DATA_DIR
from rotation import rotate_svg_file

router = APIRouter(prefix="/files", tags=["files"])

@router.get("")
def list_files():
    files = [
        path for path in DATA_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".svg"
    ]
    files.sort(key=lambda path: path.name.lower())
    return [_file_metadata(path) for path in files]


@router.post("", status_code=201)
async def upload_file(file: UploadFile):
    safe_name = _sanitize_filename(file.filename or "uploaded.svg")
    final_name = _unique_filename(safe_name)
    target = DATA_DIR / final_name

    with target.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)

    if target.stat().st_size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    return _file_metadata(target)

@router.delete("/{filename}", status_code=204)
def delete_file(filename: str):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    target.unlink()
    return Response(status_code=204)

@router.post("/{filename}/rotate", status_code=200)
def rotate_file(filename: str, request: RotateRequest):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    normalized = request.normalized
    if normalized not in {0, 90, 180, 270}:
        raise HTTPException(status_code=400, detail="Rotation angle must be a multiple of 90 degrees")

    if normalized == 0:
        return {"rotated": False, "angle": 0}

    rotate_svg_file(target, normalized)
    return {"rotated": True, "angle": normalized}

@router.post("/{filename}/rename", status_code=200)
def rename_file(filename: str, request: RenameRequest):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    new_name = request.sanitized(_sanitize_filename)
    new_path = DATA_DIR / new_name

    if new_path.exists() and new_path != target:
        raise HTTPException(status_code=409, detail="A file with that name already exists")

    if new_path == target:
        return _file_metadata(target)

    try:
        target.rename(new_path)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Unable to rename file") from exc

    return _file_metadata(new_path)

@router.get("/{filename}/download")
def download_file(filename: str):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target, media_type="image/svg+xml", filename=safe_name)

@router.get("/{filename}/preview")
def preview_file(
    filename: str,
    handling: int = Query(1, ge=1),
    speed: int = Query(70, ge=1),
    brushless: bool = False,
):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    est_seconds, est_distance = _preview_via_nextdraw(
        target,
        handling=handling,
        speed=speed,
        brushless=brushless,
    )

    # Fall back to intrinsic SVG distance if nextdraw preview isn't available.
    if est_distance is None:
        est_distance = _estimate_distance_mm(target)

    return {
        "estimated_seconds": est_seconds,
        "distance_mm": est_distance,
    }

@router.get("/{filename}/raw")
def raw_file(filename: str):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return Response(target.read_text(), media_type="image/svg+xml")

@router.post("/{filename}/plot")
def plot_file(filename: str, request: PlotRequest):
    """Start plotting an uploaded SVG file."""
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return _start_plot_from_path(
        svg_source=target,
        page=request.page,
        s_down=request.s_down,
        s_up=request.s_up,
        p_down=request.p_down,
        p_up=request.p_up,
        handling=request.handling,
        speed=request.speed,
        brushless=request.brushless,
        original_name=safe_name,
    )
