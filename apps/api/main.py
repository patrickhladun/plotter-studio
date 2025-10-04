import asyncio
import logging
import math
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Sequence

try:
    from svgpathtools import svg2paths2
except Exception:  # pragma: no cover - optional dependency
    svg2paths2 = None

from fastapi import FastAPI, UploadFile, Form, HTTPException, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from version import __version__

logger = logging.getLogger("plotterstudio.api")

ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

app = FastAPI(title="Plotter Studio", version=__version__)
JOB = {
    "proc": None,
    "file": None,
    "progress": None,
    "start_time": None,
    "end_time": None,
    "distance_mm": None,
    "error": None,
}
FRONTEND_DIST = Path(
    os.getenv("PLOTTERSTUDIO_FRONTEND_DIST")
    or os.getenv("SYNTHDRAW_FRONTEND_DIST")
    or Path(__file__).resolve().parent / "frontend"
)
DEFAULT_HOME = Path(
    os.getenv("PLOTTERSTUDIO_HOME")
    or os.getenv("SYNTHDRAW_HOME")
    or Path.home() / "plotter-studio"
)
DATA_DIR = Path(
    os.getenv("PLOTTERSTUDIO_DATA_DIR")
    or os.getenv("SYNTHDRAW_DATA_DIR")
    or DEFAULT_HOME / "uploads"
)
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _format_command(parts: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def _sanitize_filename(name: str) -> str:
    if not name:
        raise HTTPException(status_code=400, detail="Filename is required")
    candidate = Path(name).name
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", candidate)
    if not safe.lower().endswith(".svg"):
        raise HTTPException(status_code=400, detail="Only .svg files are supported")
    return safe


def _file_metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    metadata: dict[str, Any] = {
        "name": path.name,
        "size": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }
    metadata.update(_extract_svg_dimensions(path))
    return metadata


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
        logger.debug("Failed to extract SVG dimensions from %s", path, exc_info=True)

    return {
        "width": width,
        "height": height,
        "viewBox": viewbox,
    }


def _parse_length_to_px(value: str | None) -> float | None:
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    match = re.match(r"^([+-]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z%]*)$", text)
    if not match:
        return None

    numeric = float(match.group(1))
    unit = match.group(2).lower()

    factors = {
        "": 1.0,
        "px": 1.0,
        "mm": 96.0 / 25.4,
        "millimeter": 96.0 / 25.4,
        "millimeters": 96.0 / 25.4,
        "cm": 96.0 / 2.54,
        "centimeter": 96.0 / 2.54,
        "centimeters": 96.0 / 2.54,
        "m": 96.0 * 39.37007874,
        "meter": 96.0 * 39.37007874,
        "meters": 96.0 * 39.37007874,
        "in": 96.0,
        "inch": 96.0,
        "inches": 96.0,
        "pt": 96.0 / 72.0,
        "pc": 16.0,
        "q": (96.0 / 25.4) / 4.0,
    }

    factor = factors.get(unit)
    if factor is None:
        return None

    return numeric * factor


def _parse_length_to_mm(value: str | None) -> float | None:
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    match = re.match(r"^([+-]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)$", text)
    if not match:
        return None

    numeric = float(match.group(1))
    unit = match.group(2).lower()

    factors = {
        "": 1.0,
        "mm": 1.0,
        "millimeter": 1.0,
        "millimeters": 1.0,
        "cm": 10.0,
        "centimeter": 10.0,
        "centimeters": 10.0,
        "m": 1000.0,
        "meter": 1000.0,
        "meters": 1000.0,
        "in": 25.4,
        "inch": 25.4,
        "inches": 25.4,
        "pt": 25.4 / 72.0,
        "pc": 25.4 / 6.0,
        "px": 25.4 / 96.0,
        "q": 0.25,
    }

    factor = factors.get(unit)
    if factor is None:
        return None

    return numeric * factor


def _svg_namespace(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[0] + "}"
    return ""


ROTATION_WRAPPER_ID = "plotterstudio-rotation-wrapper"
ROTATION_ANGLE_ATTR = "data-plotterstudio-rotation"
ROTATION_BASE_VIEWBOX_ATTR = "data-plotterstudio-base-viewbox"
ROTATION_BASE_WIDTH_ATTR = "data-plotterstudio-base-width"
ROTATION_BASE_HEIGHT_ATTR = "data-plotterstudio-base-height"
PROGRESS_RE = re.compile(r"(\d+(?:\.\d+)?)%")
TIME_RE = re.compile(r"(?:elapsed|time)[^0-9]*([0-9]+):(\d{2})(?::(\d{2}))?", re.IGNORECASE)
DIST_RE = re.compile(r"(?:distance|travel)[^0-9]*([0-9]+(?:\.\d+)?)(\s*(?:mm|millimeters?|cm|centimeters?|m|meters?|in|inch(?:es)?))?", re.IGNORECASE)


def _watch_plot_progress(proc: subprocess.Popen[str]) -> None:
    if proc.stdout is None:
        return

    log_lines: deque[str] = deque(maxlen=200)

    try:
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            log_lines.append(line)
            logger.debug("nextdraw: %s", line)
            match = PROGRESS_RE.search(line)
            if match:
                try:
                    value = float(match.group(1))
                except ValueError:
                    continue
                JOB["progress"] = max(0.0, min(value, 100.0))
            time_match = TIME_RE.search(line)
            if time_match:
                try:
                    minutes = int(time_match.group(1))
                    seconds = int(time_match.group(2))
                    hours = 0
                    if time_match.group(3):
                        hours = minutes
                        minutes = seconds
                        seconds = int(time_match.group(3))
                    JOB["elapsed_override"] = hours * 3600 + minutes * 60 + seconds
                except ValueError:
                    pass
            dist_match = DIST_RE.search(line)
            if dist_match:
                try:
                    value = float(dist_match.group(1))
                except ValueError:
                    value = None
                unit = (dist_match.group(2) or "").strip().lower()
                if value is not None:
                    if unit in {"", "mm", "millimeter", "millimeters"}:
                        JOB["distance_mm"] = value
                    elif unit in {"cm", "centimeter", "centimeters"}:
                        JOB["distance_mm"] = value * 10.0
                    elif unit in {"m", "meter", "meters"}:
                        JOB["distance_mm"] = value * 1000.0
                    elif unit in {"in", "inch", "inches"}:
                        JOB["distance_mm"] = value * 25.4
        proc.wait()
    finally:
        if JOB.get("proc") is proc:
            JOB["proc"] = None
            JOB["end_time"] = time.time()
            if proc.returncode == 0:
                JOB["progress"] = 100.0
                JOB["error"] = None
            else:
                JOB["progress"] = None
                output_text = "\n".join(log_lines).strip()
                JOB["error"] = output_text or f"nextdraw exited with code {proc.returncode}"


def _ensure_viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    viewbox = root.get("viewBox")
    if viewbox:
        parts = re.split(r"[\s,]+", viewbox.strip())
        if len(parts) == 4:
            try:
                min_x, min_y, width, height = map(float, parts)
                return min_x, min_y, width, height
            except ValueError:
                pass

    width_px = _parse_length_to_px(root.get("width"))
    height_px = _parse_length_to_px(root.get("height"))
    if width_px is None or height_px is None:
        raise HTTPException(status_code=400, detail="Unable to determine SVG dimensions for rotation")

    root.set("viewBox", f"0 0 {width_px} {height_px}")
    return 0.0, 0.0, width_px, height_px


def _ensure_rotation_wrapper(root: ET.Element) -> ET.Element:
    ns = _svg_namespace(root.tag)
    wrapper: Optional[ET.Element] = None
    for child in list(root):
        if child.tag == f"{ns}g" and child.attrib.get("id") == ROTATION_WRAPPER_ID:
            wrapper = child
            break

    if wrapper is not None:
        return wrapper

    wrapper = ET.Element(f"{ns}g")
    wrapper.set("id", ROTATION_WRAPPER_ID)

    for child in list(root):
        wrapper.append(child)
        root.remove(child)

    root.append(wrapper)
    return wrapper


def _rotate_svg_file(path: Path, angle: int) -> None:
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
    min_x, min_y, base_width, base_height = _ensure_viewbox(root)
    wrapper = _ensure_rotation_wrapper(root)

    if ROTATION_BASE_VIEWBOX_ATTR not in wrapper.attrib:
        wrapper.set(ROTATION_BASE_VIEWBOX_ATTR, f"{min_x} {min_y} {base_width} {base_height}")
        if root.get("width"):
            wrapper.set(ROTATION_BASE_WIDTH_ATTR, root.get("width") or "")
        if root.get("height"):
            wrapper.set(ROTATION_BASE_HEIGHT_ATTR, root.get("height") or "")
        wrapper.set(ROTATION_ANGLE_ATTR, "0")

    base_viewbox_raw = wrapper.attrib.get(ROTATION_BASE_VIEWBOX_ATTR)
    if not base_viewbox_raw:
        base_viewbox_raw = f"{min_x} {min_y} {base_width} {base_height}"
        wrapper.set(ROTATION_BASE_VIEWBOX_ATTR, base_viewbox_raw)

    try:
        base_min_x, base_min_y, base_w, base_h = map(float, re.split(r"[\s,]+", base_viewbox_raw.strip()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Stored SVG metadata is invalid") from exc

    base_cx = base_min_x + base_w / 2.0
    base_cy = base_min_y + base_h / 2.0

    current_angle = int(wrapper.attrib.get(ROTATION_ANGLE_ATTR, "0")) % 360
    total_angle = (current_angle + normalized) % 360

    angle_rad = math.radians(total_angle)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    corners = [
        (base_min_x, base_min_y),
        (base_min_x + base_w, base_min_y),
        (base_min_x, base_min_y + base_h),
        (base_min_x + base_w, base_min_y + base_h),
    ]

    rotated_points = []
    for x, y in corners:
        dx = x - base_cx
        dy = y - base_cy
        rx = cos_a * dx - sin_a * dy + base_cx
        ry = sin_a * dx + cos_a * dy + base_cy
        rotated_points.append((rx, ry))

    new_min_x = min(p[0] for p in rotated_points)
    new_max_x = max(p[0] for p in rotated_points)
    new_min_y = min(p[1] for p in rotated_points)
    new_max_y = max(p[1] for p in rotated_points)
    new_width = new_max_x - new_min_x
    new_height = new_max_y - new_min_y

    root.set("viewBox", f"{new_min_x:.6f} {new_min_y:.6f} {new_width:.6f} {new_height:.6f}")

    base_width_attr = wrapper.attrib.get(ROTATION_BASE_WIDTH_ATTR)
    base_height_attr = wrapper.attrib.get(ROTATION_BASE_HEIGHT_ATTR)
    if base_width_attr is not None and base_height_attr is not None:
        if total_angle % 180 in {90, 270}:
            root.set("width", base_height_attr)
            root.set("height", base_width_attr)
        else:
            root.set("width", base_width_attr)
            root.set("height", base_height_attr)

    if total_angle == 0:
        wrapper.attrib.pop("transform", None)
    else:
        wrapper.set("transform", f"rotate({total_angle},{base_cx},{base_cy})")

    wrapper.set(ROTATION_ANGLE_ATTR, str(total_angle))

    tree.write(path, encoding="utf-8", xml_declaration=True)


def _estimate_distance_mm(path: Path) -> float | None:
    if svg2paths2 is None:
        return None

    try:
        paths, _, svg_attr = svg2paths2(str(path))
    except Exception:
        logger.debug("Failed to parse SVG for distance %s", path, exc_info=True)
        return None

    total_length = 0.0
    for geom in paths:
        try:
            total_length += float(geom.length())
        except Exception:
            continue

    if total_length == 0.0:
        return 0.0

    scale = 1.0
    viewbox_raw = svg_attr.get("viewBox") if svg_attr else None
    width_attr = svg_attr.get("width") if svg_attr else None
    height_attr = svg_attr.get("height") if svg_attr else None

    if viewbox_raw:
        parts = re.split(r"[\s,]+", viewbox_raw.strip())
        if len(parts) == 4:
            try:
                vb_width = float(parts[2])
                vb_height = float(parts[3])
            except ValueError:
                vb_width = vb_height = 0.0
            width_mm = _parse_length_to_mm(width_attr)
            height_mm = _parse_length_to_mm(height_attr)
            if vb_width and width_mm:
                scale = width_mm / vb_width
            elif vb_height and height_mm:
                scale = height_mm / vb_height
    else:
        candidate = _parse_length_to_mm(width_attr)
        if candidate:
            scale = 1.0

    return total_length * scale


def _preview_via_nextdraw(
    svg_path: Path,
    page: str,
    handling: int,
    speed: int,
    brushless: bool,
) -> tuple[Optional[float], Optional[float]]:
    args: list[str] = [*_nextdraw_base(), str(svg_path), "--preview", "--report_time"]

    model = (
        os.getenv("PLOTTERSTUDIO_MODEL")
        or os.getenv("PLOTTERSTUDIO_MODEL_NAME")
        or os.getenv("SYNTHDRAW_MODEL")
        or os.getenv("SYNTHDRAW_MODEL_NAME")
    )
    if model:
        args.extend(["--model", model])

    args.extend(["--handling", str(handling)])
    if handling == 4:
        args.extend(["-s", str(speed)])

    if brushless:
        args.extend(["--penlift", "3"])

    logger.debug("Running nextdraw preview: %s", _format_command(args))
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return None, None
    except subprocess.TimeoutExpired:
        logger.warning("nextdraw preview timed out for %s", svg_path)
        return None, None

    output = "\n".join(filter(None, [proc.stdout, proc.stderr]))
    output_text = output.strip()
    time_match = re.search(r"Estimated print time:\s*([0-9:]+)", output)
    distance_match = re.search(r"draw:\s*([0-9.]+)\s*mm", output, re.IGNORECASE)

    est_seconds: Optional[float] = None
    if time_match:
        parts = time_match.group(1).split(":")
        try:
            pieces = [int(part) for part in parts]
            if len(pieces) == 3:
                est_seconds = pieces[0] * 3600 + pieces[1] * 60 + pieces[2]
            elif len(pieces) == 2:
                est_seconds = pieces[0] * 60 + pieces[1]
            elif len(pieces) == 1:
                est_seconds = pieces[0]
        except ValueError:
            est_seconds = None

    est_distance: Optional[float] = None
    if distance_match:
        try:
            est_distance = float(distance_match.group(1))
        except ValueError:
            est_distance = None

    if proc.returncode != 0 and est_seconds is None and est_distance is None:
        if output_text:
            logger.warning(
                "nextdraw preview failed with code %s: %s",
                proc.returncode,
                output_text,
            )
        else:
            logger.warning("nextdraw preview failed with code %s", proc.returncode)

    return est_seconds, est_distance


def _preview_from_path(
    svg_path: Path,
    page: str,
    handling: int,
    speed: int,
    brushless: bool,
) -> dict[str, Any]:
    preview_secs, preview_distance = _preview_via_nextdraw(
        svg_path, page, handling, speed, brushless
    )

    if preview_secs is not None or preview_distance is not None:
        return {
            "source": "nextdraw",
            "estimated_seconds": preview_secs,
            "distance_mm": preview_distance,
        }

    distance = _estimate_distance_mm(svg_path)
    est_seconds = None
    if distance is not None:
        mm_per_sec = max(5.0, (speed or 40) / 100.0 * 35.0)
        est_seconds = distance / mm_per_sec

    return {
        "source": "estimate",
        "estimated_seconds": est_seconds,
        "distance_mm": distance,
    }


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


class PlotRequest(BaseModel):
    page: str = "a5"
    s_down: int = 30
    s_up: int = 70
    p_down: int = 40
    p_up: int = 70
    handling: int = 1
    speed: int = 70
    brushless: bool = False


class RotateRequest(BaseModel):
    angle: int = 90

    @property
    def normalized(self) -> int:
        value = self.angle % 360
        if value < 0:
            value += 360
        return value


class RenameRequest(BaseModel):
    new_name: str

    def sanitized(self) -> str:
        candidate = self.new_name.strip()
        if not candidate:
            raise HTTPException(status_code=400, detail="New filename cannot be empty")
        if not candidate.lower().endswith(".svg"):
            candidate = f"{candidate}.svg"
        return _sanitize_filename(candidate)

def _configure_frontend(app: FastAPI) -> None:
    if not FRONTEND_DIST.exists():
        logger.warning(
            "Frontend bundle directory not found at %s", FRONTEND_DIST
        )
        return

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        logger.warning(
            "Frontend bundle missing index.html at %s", index_file
        )
        return

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_file)


# Enable CORS so your Next.js frontend can talk to it
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "https://plotterstudio.netlify.app",
        "https://plotterstudio.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _nextdraw_base() -> list[str]:
    value = (
        os.getenv("PLOTTERSTUDIO_NEXTDRAW")
        or os.getenv("SYNTHDRAW_AXICLI")
        or os.getenv("NEXTDRAW_CLI")
    )
    if value:
        return shlex.split(os.path.expanduser(value))
    home = (
        os.getenv("PLOTTERSTUDIO_HOME")
        or os.getenv("PLOTTERSTUDIO_API_HOME")
        or os.getenv("SYNTHDRAW_HOME")
        or os.getenv("SYNTHDRAW_API_HOME")
    )
    if home:
        candidate = Path(home).expanduser() / "venv" / "bin" / "nextdraw"
        if candidate.exists():
            return [str(candidate)]
    return ["nextdraw"]


def _run_manual(command: str) -> subprocess.CompletedProcess[str]:
    args = [*_nextdraw_base(), "--mode", "manual", "--manual_cmd", command]
    logger.info("Running nextdraw manual command: %s", _format_command(args))
    try:
        return subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="nextdraw binary not found; set PLOTTERSTUDIO_NEXTDRAW (or legacy SYNTHDRAW_AXICLI) to the full path",
        ) from exc


def _ensure_motors_enabled() -> None:
    """Enable XY motors before attempting movement commands."""
    _manual_response("motors enabled", _run_utility("enable_xy"))


def _infer_pen_state(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    lowered = text.lower()
    if "pen" not in lowered:
        return None
    if "down" in lowered and "up" not in lowered:
        return "down"
    if "up" in lowered and "down" not in lowered:
        return "up"
    return None


def _run_utility(command: str, extra_args: Optional[Sequence[str]] = None) -> subprocess.CompletedProcess[str]:
    args = [*_nextdraw_base(), "-m", "utility", "-M", command]
    if extra_args:
        args.extend(str(item) for item in extra_args)
    logger.info("Running nextdraw utility command: %s", _format_command(args))
    try:
        return subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="nextdraw binary not found; set PLOTTERSTUDIO_NEXTDRAW (or legacy SYNTHDRAW_AXICLI) to the full path",
        ) from exc


def _manual_response(action: str, result: subprocess.CompletedProcess[str], extra: dict[str, Any] | None = None):
    payload: dict[str, Any] = {
        "ok": result.returncode == 0,
        "action": action,
        "returncode": result.returncode,
    }
    if extra:
        payload.update(extra)
    if result.stdout:
        payload["stdout"] = result.stdout.strip()
    if result.stderr:
        payload["stderr"] = result.stderr.strip()
    if not payload["ok"]:
        raise HTTPException(status_code=500, detail=payload)
    return payload


def _start_plot_from_path(
    svg_source: Path,
    page: str,
    s_down: int,
    s_up: int,
    p_down: int,
    p_up: int,
    handling: int = 1,
    speed: int = 70,
    brushless: bool = False,
    original_name: Optional[str] = None,
) -> dict[str, Any]:
    if JOB["proc"] and JOB["proc"].poll() is None:
        raise HTTPException(status_code=409, detail="A job is already running")

    if not svg_source.exists():
        raise HTTPException(status_code=404, detail="SVG not found")

    JOB["error"] = None

    temp_dir = Path(tempfile.mkdtemp(prefix="plotterstudio_plot_"))
    target_name = _sanitize_filename(original_name or svg_source.name)
    working_src = temp_dir / target_name
    shutil.copy2(svg_source, working_src)

    fixed_path = working_src.with_name(f"{working_src.stem}-fixed.svg")
    page_flag = page.lower() if page and page.lower() in {"a3", "a4", "a5", "a6"} else "a5"
    try:
        vp = subprocess.run(
            [
                "vpype",
                "read",
                str(working_src),
                "write",
                "--page-size",
                page_flag,
                "--center",
                str(fixed_path),
            ],
            capture_output=True,
            text=True,
        )
        use_path = fixed_path if vp.returncode == 0 else working_src
        if vp.returncode != 0:
            logger.warning("vpype exited with %s; falling back to original SVG", vp.returncode)
            if vp.stderr:
                logger.debug("vpype stderr: %s", vp.stderr.strip())
    except FileNotFoundError:
        logger.warning("vpype command not found; skipping centering step")
        use_path = working_src

    cmd = [
        *_nextdraw_base(),
        str(use_path),
        "--speed_pendown",
        str(s_down),
        "--speed_penup",
        str(s_up),
        "--pen_pos_down",
        str(p_down),
        "--pen_pos_up",
        str(p_up),
        "--progress",
    ]

    cmd.extend(["--handling", str(handling)])
    if handling == 4:
        cmd.extend(["-s", str(speed)])

    if brushless:
        cmd.extend(["--penlift", "3"])

    cmd_str = _format_command(cmd)
    logger.info("Launching nextdraw: %s", cmd_str)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    JOB["proc"] = proc
    current_name = os.path.basename(use_path)
    if JOB.get("file") != current_name:
        JOB["distance_mm"] = None
    JOB["file"] = current_name
    JOB["progress"] = 0.0
    JOB["start_time"] = time.time()
    JOB["end_time"] = None
    if JOB.get("distance_mm") is None:
        JOB["distance_mm"] = _estimate_distance_mm(use_path)
    JOB["elapsed_override"] = None

    # If the process exits immediately, capture output and respond with the failure.
    time.sleep(0.2)
    returncode = proc.poll()
    if returncode is not None:
        stdout_data, _ = proc.communicate()
        output_text = (stdout_data or "").strip()
        JOB["proc"] = None
        JOB["end_time"] = time.time()
        JOB["elapsed_override"] = None
        if returncode == 0:
            suspicious = output_text.lower()
            if output_text and (
                "error" in suspicious
                or "no nextdraw" in suspicious
                or "no devices" in suspicious
            ):
                JOB["progress"] = None
                JOB["error"] = output_text
                logger.error(
                    "nextdraw reported an error despite exit code 0: %s",
                    output_text,
                )
                raise HTTPException(status_code=500, detail=output_text)

            JOB["progress"] = 100.0
            JOB["error"] = None
            logger.info("nextdraw completed immediately with code 0%s", " (no output)" if not output_text else "")
            response: dict[str, Any] = {
                "ok": True,
                "pid": proc.pid,
                "file": JOB["file"],
                "cmd": cmd_str,
                "page": page_flag,
                "completed": True,
            }
            if output_text:
                response["output"] = output_text
            return response

        JOB["progress"] = None
        JOB["error"] = output_text or f"nextdraw exited with code {returncode}"
        logger.error(
            "nextdraw exited immediately with code %s: %s",
            returncode,
            output_text,
        )
        raise HTTPException(status_code=500, detail=JOB["error"])

    if proc.stdout is not None:
        threading.Thread(target=_watch_plot_progress, args=(proc,), daemon=True).start()

    return {
        "ok": True,
        "pid": proc.pid,
        "file": JOB["file"],
        "cmd": cmd_str,
        "page": page_flag,
    }


@app.post("/files", status_code=201)
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


@app.get("/files")
def list_files():
    files = [
        path
        for path in DATA_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".svg"
    ]
    files.sort(key=lambda path: path.name.lower())
    return [_file_metadata(path) for path in files]


@app.delete("/files/{filename}", status_code=204)
def delete_file(filename: str):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    target.unlink()
    return Response(status_code=204)


@app.post("/files/{filename}/rotate", status_code=200)
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

    _rotate_svg_file(target, normalized)
    return {"rotated": True, "angle": normalized}


@app.post("/files/{filename}/rename", status_code=200)
def rename_file(filename: str, request: RenameRequest):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    new_name = request.sanitized()
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


@app.get("/files/{filename}/download")
def download_file(filename: str):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target, media_type="image/svg+xml", filename=safe_name)


@app.get("/files/{filename}/preview")
def preview_file(
    filename: str,
    page: str = "a5",
    handling: int = 1,
    speed: int = 70,
    brushless: bool = False,
):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    info = _preview_from_path(target, page, handling, speed, brushless)
    JOB["file"] = safe_name
    JOB["distance_mm"] = info.get("distance_mm")
    return info


@app.get("/files/{filename}/raw")
def raw_file(filename: str):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return Response(target.read_text(), media_type="image/svg+xml")


@app.post("/files/{filename}/plot")
def plot_file(filename: str, params: PlotRequest):
    safe_name = _sanitize_filename(filename)
    target = DATA_DIR / safe_name
    return _start_plot_from_path(
        target,
        params.page,
        params.s_down,
        params.s_up,
        params.p_down,
        params.p_up,
        params.handling,
        params.speed,
        params.brushless,
        original_name=safe_name,
    )


@app.get("/status")
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


@app.get("/version")
def version():
    return {"version": __version__}


@app.post("/disable_motors")
def disable_motors():
    result = _run_utility("disable_xy")
    return _manual_response("motors disabled", result)


@app.post("/pen/toggle")
def pen_toggle():
    result = _run_utility("toggle")
    state = _infer_pen_state(result.stdout) or _infer_pen_state(result.stderr)
    extra = {"state": state} if state else None
    return _manual_response("pen toggled", result, extra)


@app.post("/pen/up")
def pen_up():
    result = _run_utility("raise_pen")
    return _manual_response("pen raised", result)


@app.post("/pen/down")
def pen_down():
    result = _run_utility("lower_pen")
    return _manual_response("pen lowered", result)


@app.post("/enable_motors")
def enable_motors():
    result = _run_utility("enable_xy")
    return _manual_response("motors enabled", result)


@app.post("/walk_home")
def walk_home():
    result = _run_utility("walk_home")
    return _manual_response("walk home", result)


@app.post("/walk")
def walk(x_mm: float = Form(0.0), y_mm: float = Form(0.0)):
    if x_mm == 0 and y_mm == 0:
        raise HTTPException(status_code=400, detail="Specify a non-zero distance for X and/or Y")

    responses: list[dict[str, Any]] = []
    if x_mm != 0:
        res_x = _run_utility("walk_mmx", ["--dist", x_mm])
        responses.append(_manual_response("walk x", res_x, {"distance_mm": x_mm}))
    if y_mm != 0:
        res_y = _run_utility("walk_mmy", ["--dist", y_mm])
        responses.append(_manual_response("walk y", res_y, {"distance_mm": y_mm}))

    if len(responses) == 1:
        return responses[0]

    combined = {
        "ok": all(item.get("ok", False) for item in responses),
        "action": "walk",
        "distance_mm": {"x": x_mm, "y": y_mm},
        "segments": responses,
    }
    if not combined["ok"]:
        raise HTTPException(status_code=500, detail=combined)
    return combined


@app.post("/move")
def move_to(x_mm: float = Form(...), y_mm: float = Form(...)):
    _ensure_motors_enabled()
    result = _run_manual(f"move_to {x_mm:.2f} {y_mm:.2f}")
    return _manual_response("move", result, {"x": x_mm, "y": y_mm})


@app.post("/home")
def move_home():
    _ensure_motors_enabled()
    result = _run_manual("move_to 0.00 0.00")
    return _manual_response("home", result, {"x": 0.0, "y": 0.0})


@app.post("/cancel")
def cancel():
    if JOB["proc"] and JOB["proc"].poll() is None:
        JOB["proc"].terminate()
        try:
            JOB["proc"].wait(timeout=3)
        except subprocess.TimeoutExpired:
            JOB["proc"].kill()
        _run_manual("raise_pen")
        _run_manual("disable_xy")
    JOB["proc"] = None
    JOB["progress"] = None
    JOB["end_time"] = time.time()
    JOB["elapsed_override"] = None
    JOB["error"] = None
    return {"ok": True, "message": "Canceled"}


@app.post("/plot")
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


_configure_frontend(app)


def _load_env_from_file(env_path: Path) -> None:
    """Load key=value pairs from a .env file without overwriting existing vars."""
    if not env_path.exists():
        return

    try:
        lines = env_path.read_text().splitlines()
    except OSError:
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def _load_default_env() -> None:
    """Attempt to load .env from common locations."""
    candidates: list[Path] = []

    env_file_var = (
        os.getenv("PLOTTERSTUDIO_ENV_FILE")
        or os.getenv("PLOTTERSTUDIO_API_ENV_FILE")
        or os.getenv("SYNTHDRAW_ENV_FILE")
        or os.getenv("SYNTHDRAW_API_ENV_FILE")
    )
    if env_file_var:
        candidates.append(Path(env_file_var).expanduser())

    api_home_env = (
        os.getenv("PLOTTERSTUDIO_HOME")
        or os.getenv("PLOTTERSTUDIO_API_HOME")
        or os.getenv("SYNTHDRAW_HOME")
        or os.getenv("SYNTHDRAW_API_HOME")
    )
    if api_home_env:
        candidates.append(Path(api_home_env).expanduser() / ".env")

    candidates.extend(
        [
            Path.cwd() / ".env",
            Path.home() / "plotter-studio" / ".env",
            Path.home() / "synthdraw" / ".env",
            Path.home() / ".config" / "plotter-studio" / ".env",
            Path.home() / ".config" / "synthdraw" / ".env",
            Path(__file__).resolve().parent / ".env",
        ]
    )

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        _load_env_from_file(resolved)


def _getenv(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value
    return default


def _run_server(args: Any) -> None:
    import uvicorn

    ssl_enabled = (
        not args.no_ssl
        and args.ssl_certfile
        and args.ssl_keyfile
    )

    uvicorn_kwargs: dict[str, Any] = {
        "host": args.host,
        "port": args.port,
        "reload": args.reload,
        "log_level": args.log_level,
    }

    if ssl_enabled:
        uvicorn_kwargs.update(
            {
                "ssl_certfile": args.ssl_certfile,
                "ssl_keyfile": args.ssl_keyfile,
                "ssl_keyfile_password": args.ssl_keyfile_password,
            }
        )

    config = uvicorn.Config("main:app", **uvicorn_kwargs)
    server = uvicorn.Server(config)
    try:
        server.run()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        if server.should_exit and not server.force_exit:
            # uvicorn waits for lingering connections; force exit to avoid hanging
            server.force_exit = True


def _print_config(args: Any) -> None:
    data = {
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "ssl_certfile": args.ssl_certfile,
        "ssl_keyfile": args.ssl_keyfile,
        "ssl_keyfile_password": "***" if args.ssl_keyfile_password else None,
        "ssl_enabled": bool(
            not args.no_ssl and args.ssl_certfile and args.ssl_keyfile
        ),
    }
    for key, value in data.items():
        if value is None:
            value = ""
        print(f"{key}: {value}")


def _build_parser() -> Any:
    import argparse

    parser = argparse.ArgumentParser(prog="plotterstudio")
    subparsers = parser.add_subparsers(dest="command")
    parser.set_defaults(command="run")

    run_parser = subparsers.add_parser(
        "run", help="Start the Plotter Studio server"
    )
    run_parser.add_argument(
        "--host",
        default=_getenv(
            "PLOTTERSTUDIO_HOST",
            "PLOTTERSTUDIO_API_HOST",
            "SYNTHDRAW_HOST",
            "SYNTHDRAW_API_HOST",
            default="0.0.0.0",
        ),
        help="Interface to bind (default: 0.0.0.0)",
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=int(
            _getenv(
                "PLOTTERSTUDIO_PORT",
                "PLOTTERSTUDIO_API_PORT",
                "SYNTHDRAW_PORT",
                "SYNTHDRAW_API_PORT",
                default="2222",
            )
        ),
        help="Port to listen on (default: 2222)",
    )
    run_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development only)",
    )
    run_parser.add_argument(
        "--log-level",
        default=_getenv(
            "PLOTTERSTUDIO_LOG_LEVEL",
            "PLOTTERSTUDIO_API_LOG_LEVEL",
            "SYNTHDRAW_LOG_LEVEL",
            "SYNTHDRAW_API_LOG_LEVEL",
            default="info",
        ),
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level (default: info)",
    )
    run_parser.add_argument(
        "--ssl-certfile",
        default=_getenv(
            "PLOTTERSTUDIO_SSL_CERTFILE",
            "PLOTTERSTUDIO_API_SSL_CERTFILE",
            "SYNTHDRAW_SSL_CERTFILE",
            "SYNTHDRAW_API_SSL_CERTFILE",
        ),
        help="Path to TLS certificate file",
    )
    run_parser.add_argument(
        "--ssl-keyfile",
        default=_getenv(
            "PLOTTERSTUDIO_SSL_KEYFILE",
            "PLOTTERSTUDIO_API_SSL_KEYFILE",
            "SYNTHDRAW_SSL_KEYFILE",
            "SYNTHDRAW_API_SSL_KEYFILE",
        ),
        help="Path to TLS private key file",
    )
    run_parser.add_argument(
        "--ssl-keyfile-password",
        default=_getenv(
            "PLOTTERSTUDIO_SSL_KEYFILE_PASSWORD",
            "PLOTTERSTUDIO_API_SSL_KEYFILE_PASSWORD",
            "SYNTHDRAW_SSL_KEYFILE_PASSWORD",
            "SYNTHDRAW_API_SSL_KEYFILE_PASSWORD",
        ),
        help="Password for the TLS private key, if encrypted",
    )
    run_parser.add_argument(
        "--no-ssl",
        action="store_true",
        help="Disable TLS even if certificate settings are present",
    )

    config_parser = subparsers.add_parser(
        "show-config", help="Print derived runtime configuration"
    )
    config_parser.add_argument(
        "--host",
        default=_getenv(
            "PLOTTERSTUDIO_HOST",
            "PLOTTERSTUDIO_API_HOST",
            "SYNTHDRAW_HOST",
            "SYNTHDRAW_API_HOST",
            default="0.0.0.0",
        ),
    )
    config_parser.add_argument(
        "--port",
        type=int,
        default=int(
            _getenv(
                "PLOTTERSTUDIO_PORT",
                "PLOTTERSTUDIO_API_PORT",
                "SYNTHDRAW_PORT",
                "SYNTHDRAW_API_PORT",
                default="2222",
            )
        ),
    )
    config_parser.add_argument(
        "--log-level",
        default=_getenv(
            "PLOTTERSTUDIO_LOG_LEVEL",
            "PLOTTERSTUDIO_API_LOG_LEVEL",
            "SYNTHDRAW_LOG_LEVEL",
            "SYNTHDRAW_API_LOG_LEVEL",
            default="info",
        ),
    )
    config_parser.add_argument(
        "--ssl-certfile",
        default=_getenv(
            "PLOTTERSTUDIO_SSL_CERTFILE",
            "PLOTTERSTUDIO_API_SSL_CERTFILE",
            "SYNTHDRAW_SSL_CERTFILE",
            "SYNTHDRAW_API_SSL_CERTFILE",
        ),
    )
    config_parser.add_argument(
        "--ssl-keyfile",
        default=_getenv(
            "PLOTTERSTUDIO_SSL_KEYFILE",
            "PLOTTERSTUDIO_API_SSL_KEYFILE",
            "SYNTHDRAW_SSL_KEYFILE",
            "SYNTHDRAW_API_SSL_KEYFILE",
        ),
    )
    config_parser.add_argument(
        "--ssl-keyfile-password",
        default=_getenv(
            "PLOTTERSTUDIO_SSL_KEYFILE_PASSWORD",
            "PLOTTERSTUDIO_API_SSL_KEYFILE_PASSWORD",
            "SYNTHDRAW_SSL_KEYFILE_PASSWORD",
            "SYNTHDRAW_API_SSL_KEYFILE_PASSWORD",
        ),
    )
    config_parser.add_argument(
        "--no-ssl",
        action="store_true",
    )

    return parser


def cli(argv: Sequence[str] | None = None) -> None:
    """CLI entry point for Plotter Studio."""

    _load_default_env()

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        _run_server(args)
    elif args.command == "show-config":
        _print_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
