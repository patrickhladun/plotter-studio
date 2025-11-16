import type { DeviceSettings } from "../lib/filesApi";

export const BASE_DEVICE_SETTINGS: DeviceSettings = {
  axicli_path: "",
  home_offset_x: 0,
  home_offset_y: 0,
  notes: "",
  penlift: 1,
  no_homing: false,
  nextdraw_model: 8, // Default model number (Bantam Tools NextDraw™ 8511)
  p_down: 40, // Default pen down position
  p_up: 70, // Default pen up position
};

export const DEVICE_DEFAULTS: Record<string, DeviceSettings> = {
  "Default Preset": {
    ...BASE_DEVICE_SETTINGS,
  },
};
