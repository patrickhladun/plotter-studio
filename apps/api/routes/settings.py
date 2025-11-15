import json
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from core.config import DATA_DIR
from core.schemas import PlotRequest, DeviceSettings


PRINT_OVERRIDES_FILE = DATA_DIR / "print_settings.local.json"
PRINT_LEGACY_FILES = (DATA_DIR / "plot_settings.json",)
DEVICE_OVERRIDES_FILE = DATA_DIR / "device_settings.local.json"


class SavePrintSettingsPayload(BaseModel):
    name: str
    settings: PlotRequest


class SaveDeviceSettingsPayload(BaseModel):
    name: str
    settings: DeviceSettings


router = APIRouter(prefix="/settings", tags=["settings"])


def _read_settings_file(path: Path) -> Dict[str, dict]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    settings = data.get("settings")
    return settings if isinstance(settings, dict) else {}


def _load_settings(primary: Path, legacy: tuple[Path, ...] = ()) -> Dict[str, dict]:
    combined: Dict[str, dict] = {}
    for path in [*legacy, primary]:
        entries = _read_settings_file(path)
        for name, value in entries.items():
            if isinstance(value, dict):
                combined[name] = value
    return combined


def _write_settings(primary: Path, settings: Dict[str, dict]) -> None:
    primary.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text(json.dumps({"settings": settings}, indent=2, sort_keys=True))


@router.get("")
@router.get("/print")
def list_print_settings():
    data = _load_settings(PRINT_OVERRIDES_FILE, PRINT_LEGACY_FILES)
    return {"settings": data}


@router.post("", status_code=201)
@router.post("/print", status_code=201)
def create_or_update_print_settings(payload: SavePrintSettingsPayload):
    overrides = _load_settings(PRINT_OVERRIDES_FILE)
    overrides[payload.name] = payload.settings.model_dump()
    _write_settings(PRINT_OVERRIDES_FILE, overrides)
    return {"name": payload.name, "settings": overrides[payload.name]}


@router.delete("/{name}", status_code=204)
@router.delete("/print/{name}", status_code=204)
def delete_print_settings(name: str):
    overrides = _read_settings_file(PRINT_OVERRIDES_FILE)
    if name not in overrides:
        raise HTTPException(status_code=404, detail="Override not found")
    del overrides[name]
    _write_settings(PRINT_OVERRIDES_FILE, overrides)
    return Response(status_code=204)


@router.get("/devices")
def list_device_settings():
    data = _load_settings(DEVICE_OVERRIDES_FILE)
    return {"settings": data}


@router.post("/devices", status_code=201)
def create_or_update_device_settings(payload: SaveDeviceSettingsPayload):
    overrides = _load_settings(DEVICE_OVERRIDES_FILE)
    overrides[payload.name] = payload.settings.model_dump()
    _write_settings(DEVICE_OVERRIDES_FILE, overrides)
    return {"name": payload.name, "settings": overrides[payload.name]}


@router.delete("/devices/{name}", status_code=204)
def delete_device_settings(name: str):
    overrides = _load_settings(DEVICE_OVERRIDES_FILE)
    if name not in overrides:
        raise HTTPException(status_code=404, detail="Override not found")
    del overrides[name]
    _write_settings(DEVICE_OVERRIDES_FILE, overrides)
    return Response(status_code=204)
