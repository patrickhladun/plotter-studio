import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import DEFAULT_HOME

router = APIRouter(prefix="/config", tags=["config"])
logger = logging.getLogger("plotterstudio.api")

CONFIG_FILE = DEFAULT_HOME / "config.json"


class DeviceConfig(BaseModel):
    selectedDeviceProfile: str | None = None
    defaultDeviceOverride: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    """Load config from file, return empty dict if file doesn't exist."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with CONFIG_FILE.open("r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load config file: %s", e)
        return {}


def _save_config(config: dict[str, Any]) -> None:
    """Save config to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with CONFIG_FILE.open("w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error("Failed to save config file: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


@router.get("/device")
def get_device_config() -> DeviceConfig:
    """Get device configuration from config file."""
    config = _load_config()
    return DeviceConfig(
        selectedDeviceProfile=config.get("selectedDeviceProfile"),
        defaultDeviceOverride=config.get("defaultDeviceOverride"),
    )


@router.post("/device")
def save_device_config(config: DeviceConfig) -> dict[str, str]:
    """Save device configuration to config file."""
    try:
        current_config = _load_config()
        if config.selectedDeviceProfile is not None:
            current_config["selectedDeviceProfile"] = config.selectedDeviceProfile
        if config.defaultDeviceOverride is not None:
            current_config["defaultDeviceOverride"] = config.defaultDeviceOverride
        _save_config(current_config)
        logger.info("Device config saved: selectedProfile=%s", config.selectedDeviceProfile)
        return {"ok": True, "message": "Config saved"}
    except Exception as e:
        logger.exception("Error saving device config: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")

