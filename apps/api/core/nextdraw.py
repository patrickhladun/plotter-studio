import os
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
import logging
from collections import deque
from pathlib import Path
from typing import Any, Optional, Sequence
from fastapi import HTTPException

try:
    from svgpathtools import svg2paths2
except ImportError:
    svg2paths2 = None

from core.config import OFFLINE_MODE
from core.state import JOB
from core.utils import _sanitize_filename

logger = logging.getLogger("plotterstudio.api")

# Regex patterns for parsing nextdraw output
PROGRESS_RE = re.compile(r"(?:Progress|Percent complete):\s*([0-9.]+)\s*%", re.IGNORECASE)
TIME_RE = re.compile(r"(?:Elapsed|Time):\s*(\d+):(\d+)(?::(\d+))?", re.IGNORECASE)
DIST_RE = re.compile(r"(?:Distance|draw):\s*([0-9.]+)\s*([a-zA-Z]*)", re.IGNORECASE)

# Mapping from Plotter model names to model numbers for -L flag
NEXTDRAW_MODEL_MAP = {
    'AxiDraw V2, V3, or SE/A4': 1,
    'AxiDraw V3/A3 or SE/A3': 2,
    'AxiDraw V3 XLX': 3,
    'AxiDraw MiniKit': 4,
    'AxiDraw SE/A1': 5,
    'AxiDraw SE/A2': 6,
    'AxiDraw V3/B6': 7,
    'Bantam Tools NextDraw™ 8511 (Default)': 8,
    'Bantam Tools NextDraw™ 1117': 9,
    'Bantam Tools NextDraw™ 2234': 10,
}


def _get_model_number(model_name: Optional[str]) -> Optional[int]:
    """Convert Plotter model name to model number for -L flag."""
    if not model_name:
        return None
    # Check exact match first
    if model_name in NEXTDRAW_MODEL_MAP:
        return NEXTDRAW_MODEL_MAP[model_name]
    # Check if it's already a number (as string)
    try:
        model_num = int(model_name)
        if 1 <= model_num <= 10:
            return model_num
    except (ValueError, TypeError):
        pass
    # Default to model 8 (Bantam Tools NextDraw™ 8511) if not found
    logger.warning("Unknown Plotter model '%s', defaulting to model 8", model_name)
    return 8


def _format_command(args):
    """Return a clean string version of the nextdraw command."""
    if isinstance(args, (list, tuple)):
        return " ".join(str(a) for a in args)
    return str(args)


def _offline_completed_process(
    args: Sequence[str],
    context: str,
) -> subprocess.CompletedProcess[str]:
    note = f"[offline:{context}] {_format_command(args)}"
    return subprocess.CompletedProcess(args=args, returncode=0, stdout=note, stderr="")


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


def _run_command(command: str) -> subprocess.CompletedProcess[str]:
    """Execute a raw nextdraw command string. The command should already include all flags.
    
    The command string from the dashboard will start with 'nextdraw', but we replace it
    with the configured base command (which may be a custom path).
    """
    logger.info("Received command string: %s", command)
    
    # Parse the command string into arguments
    parts = shlex.split(command)
    logger.info("Parsed command parts: %s", parts)
    
    # Replace 'nextdraw' with the configured base command
    if parts and parts[0] == 'nextdraw':
        base_cmd = _nextdraw_base()
        logger.info("Base command resolved to: %s", base_cmd)
        args = [*base_cmd, *parts[1:]]
    else:
        # If it doesn't start with 'nextdraw', use as-is (might be a full path)
        args = parts
    
    logger.info("Final command to execute: %s", _format_command(args))
    logger.info("Command args list: %s", args)
    
    if OFFLINE_MODE:
        logger.info("Offline mode: skipping command execution.")
        return _offline_completed_process(args, "command")
    try:
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
        )
        logger.info("Command executed. Return code: %d", result.returncode)
        if result.stdout:
            logger.info("Command stdout: %s", result.stdout[:500])  # First 500 chars
        if result.stderr:
            logger.warning("Command stderr: %s", result.stderr[:500])  # First 500 chars
        return result
    except FileNotFoundError as exc:
        logger.error("nextdraw binary not found. Searched for: %s", args[0] if args else "unknown")
        raise HTTPException(
            status_code=500,
            detail="nextdraw binary not found; set PLOTTERSTUDIO_NEXTDRAW (or legacy SYNTHDRAW_AXICLI) to the full path",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error executing command: %s", exc)
        raise


def _run_manual(command: str, model: Optional[str] = None) -> subprocess.CompletedProcess[str]:
    # Get model from parameter, JOB state, or environment
    resolved_model = model or JOB.get("model") or (
        os.getenv("PLOTTERSTUDIO_MODEL")
        or os.getenv("PLOTTERSTUDIO_MODEL_NAME")
        or os.getenv("SYNTHDRAW_MODEL")
        or os.getenv("SYNTHDRAW_MODEL_NAME")
    )
    model_number = _get_model_number(resolved_model)
    
    args = [*_nextdraw_base()]
    if model_number:
        args.append(f"-L{model_number}")
    args.extend(["--mode", "manual", "--manual_cmd", command])
    logger.info("Running nextdraw manual command: %s", _format_command(args))
    if OFFLINE_MODE:
        logger.info("Offline mode: skipping manual command execution.")
        return _offline_completed_process(args, "manual")
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


def _run_utility(command: str, extra_args: Optional[Sequence[str]] = None, model: Optional[str] = None) -> subprocess.CompletedProcess[str]:
    # Get model from parameter, JOB state, or environment
    resolved_model = model or JOB.get("model") or (
        os.getenv("PLOTTERSTUDIO_MODEL")
        or os.getenv("PLOTTERSTUDIO_MODEL_NAME")
        or os.getenv("SYNTHDRAW_MODEL")
        or os.getenv("SYNTHDRAW_MODEL_NAME")
    )
    model_number = _get_model_number(resolved_model)
    
    args = [*_nextdraw_base()]
    if model_number:
        args.append(f"-L{model_number}")
    args.extend(["-m", "utility", "-M", command])
    if extra_args:
        args.extend(str(item) for item in extra_args)
    logger.info("Running nextdraw cli command: %s", _format_command(args))
    if OFFLINE_MODE:
        logger.info("Offline mode: skipping utility command execution.")
        return _offline_completed_process(args, "utility")
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
            detail="nextdraw binary not found; set PLOTTERSTUDIO_NEXTDRAW to the full path",
        ) from exc


def _manual_response(
    action: str,
    result: subprocess.CompletedProcess[str],
    extra: dict[str, Any] | None = None,
    *,
    error_on_failure: bool = True,
):
    payload: dict[str, Any] = {
        "ok": result.returncode == 0,
        "action": action,
        "returncode": result.returncode,
    }
    command_args = getattr(result, "args", None)
    if command_args:
        payload["command"] = _format_command(command_args)
    if extra:
        payload.update(extra)
    if result.stdout:
        payload["stdout"] = result.stdout.strip()
    if result.stderr:
        payload["stderr"] = result.stderr.strip()
    if not payload["ok"] and error_on_failure:
        raise HTTPException(status_code=500, detail=payload)
    return payload


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


def _preview_via_nextdraw(
    svg_path: Path,
    handling: int,
    speed: int,
    penlift: Optional[int] = None,
    model: Optional[str] = None,
) -> tuple[Optional[float], Optional[float]]:
    if OFFLINE_MODE:
        logger.info("Offline mode: skipping preview run for %s", svg_path)
        return None, _estimate_distance_mm(svg_path)

    resolved_model = model or (
        os.getenv("PLOTTERSTUDIO_MODEL")
        or os.getenv("PLOTTERSTUDIO_MODEL_NAME")
        or os.getenv("SYNTHDRAW_MODEL")
        or os.getenv("SYNTHDRAW_MODEL_NAME")
    )
    model_number = _get_model_number(resolved_model)
    
    args: list[str] = [*_nextdraw_base()]
    if model_number:
        args.append(f"-L{model_number}")
    args.extend([str(svg_path), "--preview", "--report_time"])

    effective_handling = None if handling == 5 else handling
    if effective_handling is not None:
        args.extend(["--handling", str(effective_handling)])
        if effective_handling == 4:
            args.extend(["-s", str(speed)])

    if penlift in {1, 2, 3}:
        args.extend(["--penlift", str(penlift)])

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


def _start_plot_from_path(
    svg_source: Path,
    page: str,
    s_down: int,
    s_up: int,
    p_down: int,
    p_up: int,
    handling: int = 1,
    speed: int = 70,
    penlift: Optional[int] = None,
    no_homing: bool = False,
    model: Optional[str] = None,
    layer: Optional[str] = None,
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
    use_path = working_src
    if not OFFLINE_MODE:
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

    model_number = _get_model_number(model)
    
    cmd = [*_nextdraw_base()]
    if model_number:
        cmd.append(f"-L{model_number}")
    cmd.extend([
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
    ])

    effective_handling = None if handling == 5 else handling
    if effective_handling is not None:
        cmd.extend(["--handling", str(effective_handling)])
        if effective_handling == 4:
            cmd.extend(["-s", str(speed)])

    if penlift in {1, 2, 3}:
        cmd.extend(["--penlift", str(penlift)])
    if no_homing:
        cmd.append("--no_homing")
    if layer:
        cmd.extend(["--layer", layer])

    cmd_str = _format_command(cmd)
    logger.info("Launching nextdraw: %s", cmd_str)

    if OFFLINE_MODE:
        logger.info("Offline mode: command not executed.")
        JOB["proc"] = None
        current_name = os.path.basename(use_path)
        JOB["file"] = current_name
        JOB["progress"] = 100.0
        JOB["start_time"] = time.time()
        JOB["end_time"] = JOB["start_time"]
        JOB["distance_mm"] = JOB.get("distance_mm") or _estimate_distance_mm(use_path)
        JOB["elapsed_override"] = 0.0
        JOB["error"] = None
        # Store the model in JOB state for offline mode too
        JOB["model"] = model
        return {
            "ok": True,
            "pid": 0,
            "file": current_name,
            "cmd": cmd_str,
            "page": page_flag,
            "completed": True,
            "offline": True,
            "output": "offline mode: command logged but not executed",
        }

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
    # Store the model in JOB state so manual/utility commands can use it
    JOB["model"] = model
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


def _ensure_motors_enabled() -> None:
    """Enable XY motors before attempting movement commands."""
    _manual_response("motors enabled", _run_utility("enable_xy"))


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


__all__ = [
    "_nextdraw_base",
    "_run_manual",
    "_run_utility",
    "_manual_response",
    "_watch_plot_progress",
    "_preview_via_nextdraw",
    "_estimate_distance_mm",
    "_start_plot_from_path",
    "_infer_pen_state",
    "_ensure_motors_enabled",
]
