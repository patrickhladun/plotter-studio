import type { PlotSettings } from "../lib/filesApi";

export const BASE_PLOT_SETTINGS: PlotSettings = {
  page: "a5",
  s_down: 30,
  s_up: 70,
  p_down: 40,
  p_up: 70,
  handling: 1,
  speed: 70,
};

export const PRINT_DEFAULTS: Record<string, PlotSettings> = {
  Default: {
    page: "a5",
    s_down: 30,
    s_up: 70,
    p_down: 40,
    p_up: 70,
    handling: 1,
    speed: 70,
  },
};