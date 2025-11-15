import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from core.config import DATA_DIR


def _extract_svg_dimensions(path: Path) -> dict[str, Any]:
    width: Optional[str] = None
    height: Optional[str] = None
    viewbox: Optional[str] = None

    try:
        tree = ET.parse(path)
        root = tree.getroot()
        if root.tag.lower().endswith("svg"):
            width = root.attrib.get("width")
            height = root.attrib.get("height")
            viewbox = root.attrib.get("viewBox")
    except Exception:
        pass

    return {"width": width, "height": height, "viewBox": viewbox}


def _file_metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    metadata = {
        "name": path.name,
        "size": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }
    metadata.update(_extract_svg_dimensions(path))
    return metadata


def _unique_filename(base: str) -> str:
    candidate = DATA_DIR / base
    if not candidate.exists():
        return base

    stem = Path(base).stem
    suffix = Path(base).suffix
    counter = 1
    while True:
        candidate_name = f"{stem}_{counter}{suffix}"
        if not (DATA_DIR / candidate_name).exists():
            return candidate_name
        counter += 1
