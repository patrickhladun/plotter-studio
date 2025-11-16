import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import DEFAULT_HOME

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger("plotterstudio.api")

# Settings directory - store all settings JSON files here
SETTINGS_DIR = DEFAULT_HOME / "settings"
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

# Settings file paths
DEVICE_PRESETS_FILE = SETTINGS_DIR / "device_presets.json"
PRINT_PRESETS_FILE = SETTINGS_DIR / "print_presets.json"
SELECTED_PROFILES_FILE = SETTINGS_DIR / "selected_profiles.json"


def _load_json_file(file_path: Path, default: Any = None) -> Any:
    """Load JSON from file, return default if file doesn't exist."""
    if not file_path.exists():
        return default if default is not None else {}
    try:
        with file_path.open("r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load settings file %s: %s", file_path, e)
        return default if default is not None else {}


def _save_json_file(file_path: Path, data: Any) -> None:
    """Save data as JSON to file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved settings to %s", file_path)
    except Exception as e:
        logger.error("Failed to save settings file %s: %s", file_path, e)
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {e}")


# Device Presets
@router.get("/device-presets")
def get_device_presets() -> dict[str, Any]:
    """Get all device presets."""
    return _load_json_file(DEVICE_PRESETS_FILE, {})


@router.post("/device-presets")
def save_device_presets(presets: dict[str, Any]) -> dict[str, Any]:
    """Save device presets."""
    _save_json_file(DEVICE_PRESETS_FILE, presets)
    return {"ok": True, "message": "Device presets saved"}


# Print Presets
@router.get("/print-presets")
def get_print_presets() -> dict[str, Any]:
    """Get all print presets."""
    return _load_json_file(PRINT_PRESETS_FILE, {})


@router.post("/print-presets")
def save_print_presets(presets: dict[str, Any]) -> dict[str, Any]:
    """Save print presets."""
    _save_json_file(PRINT_PRESETS_FILE, presets)
    return {"ok": True, "message": "Print presets saved"}


# Selected Profiles
@router.get("/selected-profiles")
def get_selected_profiles() -> dict[str, Any]:
    """Get selected device and print profiles."""
    return _load_json_file(SELECTED_PROFILES_FILE, {
        "deviceProfile": None,
        "printProfile": None,
    })


@router.post("/selected-profiles")
def save_selected_profiles(profiles: dict[str, str | None]) -> dict[str, Any]:
    """Save selected device and print profiles."""
    _save_json_file(SELECTED_PROFILES_FILE, profiles)
    return {"ok": True, "message": "Selected profiles saved"}

