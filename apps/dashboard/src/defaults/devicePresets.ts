import type { DeviceSettings } from '../lib/filesApi';

export const BASE_DEVICE_SETTINGS: DeviceSettings = {
  host: 'localhost',
  port: 2222,
  axicli_path: '',
  home_offset_x: 0,
  home_offset_y: 0,
  notes: '',
  penlift: 1,
  no_homing: false,
  nextdraw_model: 'Bantam Tools NextDraw™ 8511 (Default)',
};

export const DEVICE_DEFAULTS: Record<string, DeviceSettings> = {
  'Default Device': {
    ...BASE_DEVICE_SETTINGS,
  },
};
