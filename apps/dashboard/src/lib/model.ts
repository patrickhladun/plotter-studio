import { writable, get } from 'svelte/store';
import { DEFAULT_MODEL_NUMBER, getModelNumber } from './nextdrawCommands';

// Model store - single source of truth for the current model number
const store = writable<number>(DEFAULT_MODEL_NUMBER);

export const model = {
  subscribe: store.subscribe,
  set: (modelNumber: number) => {
    if (modelNumber >= 1 && modelNumber <= 10) {
      store.set(modelNumber);
    } else {
      console.warn(`Invalid model number ${modelNumber}, using default ${DEFAULT_MODEL_NUMBER}`);
      store.set(DEFAULT_MODEL_NUMBER);
    }
  },
  update: (fn: (current: number) => number) => {
    store.update((current) => {
      const updated = fn(current);
      if (updated >= 1 && updated <= 10) {
        return updated;
      }
      console.warn(`Invalid model number ${updated}, keeping current ${current}`);
      return current;
    });
  },
};

/**
 * Get model flag string (e.g., "-L8") for use in command building
 * Returns empty string if model is invalid
 * Uses the current store value by default
 * @returns Model flag string like "-L8" or empty string
 */
export const getFlag = (): string => {
  const num = getModelNumber(get(store));
  if (num === null) {
    return "";
  }
  return `-L${num}`;
};

/**
 * Build a complete nextdraw plot command with model flag
 * @param filename - SVG filename to plot
 * @param settings - Plot settings
 * @returns Complete nextdraw command string
 */
export const buildPlotCommand = (filename: string, settings: {
  page?: string;
  s_down?: number;
  s_up?: number;
  p_down?: number;
  p_up?: number;
  handling?: number;
  speed?: number;
  penlift?: number;
  no_homing?: boolean;
  layer?: string | null;
}): string => {
  const parts = ['nextdraw', getFlag()].filter(Boolean);
  
  // Add filename
  parts.push(filename);
  
  // Add speed settings
  if (settings.s_down !== undefined) {
    parts.push('--speed_pendown', String(settings.s_down));
  }
  if (settings.s_up !== undefined) {
    parts.push('--speed_penup', String(settings.s_up));
  }
  
  // Add pen position settings
  if (settings.p_down !== undefined) {
    parts.push('--pen_pos_down', String(settings.p_down));
  }
  if (settings.p_up !== undefined) {
    parts.push('--pen_pos_up', String(settings.p_up));
  }
  
  // Add handling mode
  const handling = settings.handling;
  if (handling !== undefined && handling !== 5) {
    parts.push('--handling', String(handling));
    if (handling === 4 && settings.speed !== undefined) {
      parts.push('-s', String(settings.speed));
    }
  }
  
  // Add penlift
  if (settings.penlift !== undefined && settings.penlift >= 1 && settings.penlift <= 3) {
    parts.push('--penlift', String(settings.penlift));
  }
  
  // Add no_homing flag
  if (settings.no_homing) {
    parts.push('--no_homing');
  }
  
  // Add layer
  if (settings.layer) {
    parts.push('--layer', settings.layer);
  }
  
  // Add progress flag
  parts.push('--progress');
  
  return parts.join(' ');
};

