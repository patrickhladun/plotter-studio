import type { DeviceSettings } from "../lib/filesApi";

export const BASE_DEVICE_SETTINGS: DeviceSettings = {
  model: "AxiDraw V3",
  host: "localhost",
  port: 2222,
  axicli_path: "",
  home_offset_x: 0,
  home_offset_y: 0,
  notes: "",
  penlift: 1,
  no_homing: true,
};

export const DEVICE_DEFAULTS: Record<string, DeviceSettings> = {
  "AxiDraw V3": {
    ...BASE_DEVICE_SETTINGS,
  },
};
