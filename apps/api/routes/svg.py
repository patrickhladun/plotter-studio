import logging
import xml.etree.ElementTree as ET
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

logger = logging.getLogger("plotterstudio.api.files")

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
    import time
    upload_start = time.time()
    safe_name = _sanitize_filename(file.filename or "uploaded.svg")
    final_name = _unique_filename(safe_name)
    target = DATA_DIR / final_name

    logger.info("=" * 60)
    logger.info("UPLOAD REQUEST STARTED")
    logger.info("  Original filename: %s", file.filename)
    logger.info("  Safe name: %s", safe_name)
    logger.info("  Final name: %s", final_name)
    logger.info("  Target path: %s", target)
    logger.info("  Content type: %s", file.content_type)
    logger.info("  Headers: %s", dict(file.headers) if hasattr(file, 'headers') else 'N/A')
    
    try:
        bytes_written = 0
        chunk_count = 0
        with target.open("wb") as handle:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                bytes_written += len(chunk)
                chunk_count += 1
        logger.info("  Wrote %d bytes in %d chunks", bytes_written, chunk_count)
    except PermissionError as exc:
        logger.exception("PERMISSION ERROR while saving %s", target)
        raise HTTPException(status_code=500, detail="Server cannot write to uploads directory") from exc
    except OSError as exc:
        logger.exception("OS ERROR writing uploaded file %s", target)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file") from exc
    except Exception as exc:
        logger.exception("UNEXPECTED ERROR during file write: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(exc)}") from exc

    try:
        size = target.stat().st_size
        logger.info("  File size on disk: %d bytes", size)
    except OSError as exc:
        logger.exception("ERROR: Unable to stat saved file %s", target)
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Unable to finalize upload") from exc

    if size == 0:
        logger.warning("WARNING: Uploaded file %s was empty; removing", target)
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    upload_duration = time.time() - upload_start
    metadata = _file_metadata(target)
    logger.info("UPLOAD SUCCESS")
    logger.info("  File: %s", target.name)
    logger.info("  Size: %d bytes", size)
    logger.info("  Duration: %.2f seconds", upload_duration)
    logger.info("=" * 60)
    return metadata

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
    penlift: int | None = Query(None, ge=1, le=3),
    model: str | None = Query(None),
):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    penlift_value = penlift if penlift in {1, 2, 3} else None

    est_seconds, est_distance = _preview_via_nextdraw(
        target,
        handling=handling,
        speed=speed,
        penlift=penlift_value,
        model=model,
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

@router.get("/{filename}/layers")
def get_layers(filename: str):
    """Extract layer IDs from an SVG file. Layers are identified by elements with id attributes."""
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        tree = ET.parse(target)
        root = tree.getroot()
        
        # Find all elements with id attributes
        layers = []
        for elem in root.iter():
            layer_id = elem.get('id')
            if layer_id:
                # Filter out common SVG element IDs that aren't typically layers
                # (like gradients, patterns, etc.)
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag not in ['linearGradient', 'radialGradient', 'pattern', 'clipPath', 'mask', 'defs']:
                    layers.append(layer_id)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_layers = []
        for layer_id in layers:
            if layer_id not in seen:
                seen.add(layer_id)
                unique_layers.append(layer_id)
        
        return {"layers": unique_layers}
    except ET.ParseError as exc:
        logger.warning("Failed to parse SVG for layers: %s", exc)
        return {"layers": []}
    except Exception as exc:
        logger.exception("Error extracting layers from SVG: %s", exc)
        return {"layers": []}

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
        penlift=request.penlift_value,
        no_homing=request.no_homing,
        model=request.model,
        layer=request.layer,
        original_name=safe_name,
    )
