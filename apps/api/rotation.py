import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from fastapi import HTTPException
import logging

logger = logging.getLogger("plotterstudio.rotation")

# --- Rotation metadata constants ---
ROTATION_WRAPPER_ID = "plotterstudio-rotation-wrapper"
ROTATION_ANGLE_ATTR = "data-plotterstudio-rotation"
ROTATION_BASE_VIEWBOX_ATTR = "data-plotterstudio-base-viewbox"
ROTATION_BASE_WIDTH_ATTR = "data-plotterstudio-base-width"
ROTATION_BASE_HEIGHT_ATTR = "data-plotterstudio-base-height"

# --- Utility functions ---

def _svg_namespace(tag: str) -> str:
    """Extract XML namespace prefix (if any)."""
    if tag.startswith("{"):
        return tag.split("}", 1)[0] + "}"
    return ""

def _parse_length_to_px(value: str | None) -> float | None:
    """Convert units like mm/cm/in/pt to px (used for viewBox fallback)."""
    if not value:
        return None

    text = value.strip()
    match = re.match(r"^([+-]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z%]*)$", text)
    if not match:
        return None

    numeric = float(match.group(1))
    unit = match.group(2).lower()

    factors = {
        "": 1.0,
        "px": 1.0,
        "mm": 96.0 / 25.4,
        "cm": 96.0 / 2.54,
        "in": 96.0,
        "pt": 96.0 / 72.0,
    }
    factor = factors.get(unit)
    return numeric * factor if factor else None

def _ensure_viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    """Ensure the SVG root has a viewBox and return (min_x, min_y, width, height)."""
    viewbox = root.get("viewBox")
    if viewbox:
        parts = re.split(r"[\s,]+", viewbox.strip())
        if len(parts) == 4:
            try:
                return tuple(map(float, parts))
            except ValueError:
                pass

    width_px = _parse_length_to_px(root.get("width"))
    height_px = _parse_length_to_px(root.get("height"))
    if width_px is None or height_px is None:
        raise HTTPException(status_code=400, detail="Unable to determine SVG dimensions for rotation")

    root.set("viewBox", f"0 0 {width_px} {height_px}")
    return 0.0, 0.0, width_px, height_px

def _ensure_rotation_wrapper(root: ET.Element) -> ET.Element:
    """Ensure a <g> wrapper exists around SVG content for rotation."""
    ns = _svg_namespace(root.tag)
    for child in list(root):
        if child.tag == f"{ns}g" and child.attrib.get("id") == ROTATION_WRAPPER_ID:
            return child

    wrapper = ET.Element(f"{ns}g")
    wrapper.set("id", ROTATION_WRAPPER_ID)
    for child in list(root):
        wrapper.append(child)
        root.remove(child)
    root.append(wrapper)
    return wrapper

# --- Main rotation logic ---

def rotate_svg_file(path: Path, angle: int) -> None:
    """Rotate an SVG by multiples of 90°, preserving viewBox and size."""
    normalized = angle % 360
    if normalized < 0:
        normalized += 360
    if normalized == 0:
        return

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise HTTPException(status_code=400, detail="Invalid SVG content") from exc

    root = tree.getroot()
    min_x, min_y, base_w, base_h = _ensure_viewbox(root)
    wrapper = _ensure_rotation_wrapper(root)

    # Store base attributes if missing
    if ROTATION_BASE_VIEWBOX_ATTR not in wrapper.attrib:
        wrapper.set(ROTATION_BASE_VIEWBOX_ATTR, f"{min_x} {min_y} {base_w} {base_h}")
        wrapper.set(ROTATION_BASE_WIDTH_ATTR, root.get("width") or "")
        wrapper.set(ROTATION_BASE_HEIGHT_ATTR, root.get("height") or "")
        wrapper.set(ROTATION_ANGLE_ATTR, "0")

    # Parse stored metadata
    base_viewbox = wrapper.attrib.get(ROTATION_BASE_VIEWBOX_ATTR, f"{min_x} {min_y} {base_w} {base_h}")
    base_min_x, base_min_y, base_w, base_h = map(float, re.split(r"[\s,]+", base_viewbox.strip()))

    base_cx = base_min_x + base_w / 2.0
    base_cy = base_min_y + base_h / 2.0

    current_angle = int(wrapper.attrib.get(ROTATION_ANGLE_ATTR, "0")) % 360
    total_angle = (current_angle + normalized) % 360

    # Rotate bounding box
    angle_rad = math.radians(total_angle)
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)

    corners = [
        (base_min_x, base_min_y),
        (base_min_x + base_w, base_min_y),
        (base_min_x, base_min_y + base_h),
        (base_min_x + base_w, base_min_y + base_h),
    ]
    rotated = [
        (cos_a * (x - base_cx) - sin_a * (y - base_cy) + base_cx,
         sin_a * (x - base_cx) + cos_a * (y - base_cy) + base_cy)
        for x, y in corners
    ]

    new_min_x = min(p[0] for p in rotated)
    new_max_x = max(p[0] for p in rotated)
    new_min_y = min(p[1] for p in rotated)
    new_max_y = max(p[1] for p in rotated)

    root.set("viewBox", f"{new_min_x:.6f} {new_min_y:.6f} {new_max_x - new_min_x:.6f} {new_max_y - new_min_y:.6f}")

    # Swap width/height on 90° and 270°
    if total_angle % 180 in {90, 270}:
        root.set("width", wrapper.attrib.get(ROTATION_BASE_HEIGHT_ATTR, root.get("height", "")))
        root.set("height", wrapper.attrib.get(ROTATION_BASE_WIDTH_ATTR, root.get("width", "")))
    else:
        root.set("width", wrapper.attrib.get(ROTATION_BASE_WIDTH_ATTR, root.get("width", "")))
        root.set("height", wrapper.attrib.get(ROTATION_BASE_HEIGHT_ATTR, root.get("height", "")))

    # Update transform
    if total_angle == 0:
        wrapper.attrib.pop("transform", None)
    else:
        wrapper.set("transform", f"rotate({total_angle},{base_cx},{base_cy})")

    wrapper.set(ROTATION_ANGLE_ATTR, str(total_angle))
    tree.write(path, encoding="utf-8", xml_declaration=True)