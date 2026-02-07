import { writable, get } from "svelte/store";
import { DEFAULT_MODEL_NUMBER, getModelNumber } from "./nextdrawCommands";

// Model store - single source of truth for the current model number
const store = writable<number>(DEFAULT_MODEL_NUMBER);

export const model = {
  subscribe: store.subscribe,
  set: (modelNumber: number) => {
    if (modelNumber >= 1 && modelNumber <= 10) {
      store.set(modelNumber);
    } else {
      console.warn(
        `Invalid model number ${modelNumber}, using default ${DEFAULT_MODEL_NUMBER}`
      );
      store.set(DEFAULT_MODEL_NUMBER);
    }
  },
  update: (fn: (current: number) => number) => {
    store.update((current) => {
      const updated = fn(current);
      if (updated >= 1 && updated <= 10) {
        return updated;
      }
      console.warn(
        `Invalid model number ${updated}, keeping current ${current}`
      );
      return current;
    });
  },
};

/**
 * Device and print settings store
 * Centralized source for pen positions and other settings used by action components
 */
export interface DevicePrintSettings {
  p_down: number;  // Pen down position (0-100)
  p_up: number;    // Pen up position (0-100)
  penlift: number; // Pen lift mode (1-3)
  s_down: number;  // Speed pen down
  s_up: number;    // Speed pen up
  handling: number; // Handling mode
  speed: number;    // Overall speed
}

const defaultSettings: DevicePrintSettings = {
  p_down: 40,
  p_up: 70,
  penlift: 1,
  s_down: 30,
  s_up: 70,
  handling: 1,
  speed: 70,
};

const settingsStore = writable<DevicePrintSettings>(defaultSettings);

export const settings = {
  subscribe: settingsStore.subscribe,
  set: (newSettings: DevicePrintSettings) => {
    settingsStore.set(newSettings);
  },
  update: (fn: (current: DevicePrintSettings) => DevicePrintSettings) => {
    settingsStore.update(fn);
  },
};

/**
 * Get model flag string (e.g., "-L8") for use in command building
 * Returns empty string if model is invalid
 * Uses the current store value by default
 * @returns Model flag string like "-L8" or empty string
 */
function getFlag(): string {
  const num = getModelNumber(get(store));
  if (num === null) {
    return "";
  }
  return `-L${num}`;
}

/**
 * Get current pen positions from settings store
 * @returns Object with p_down and p_up values
 */
export function getPenPositions(): { p_down: number; p_up: number } {
  const current = get(settingsStore);
  return {
    p_down: current.p_down,
    p_up: current.p_up,
  };
}

/**
 * Get pen position flags for use in command building
 * @returns Array of command flags like ["--pen_pos_down", "40", "--pen_pos_up", "70"]
 */
export function getPenFlags(): string[] {
  const { p_down, p_up } = getPenPositions();
  const flags: string[] = [];

  if (Number.isFinite(p_down)) {
    flags.push("--pen_pos_down", String(p_down));
  }
  if (Number.isFinite(p_up)) {
    flags.push("--pen_pos_up", String(p_up));
  }

  return flags;
}

export { getFlag };

/**
 * Extract layer number from layer name (e.g., "layer1" -> "1", "layer2" -> "2")
 * @param layerName - Layer name like "layer1", "layer2", etc.
 * @returns The numeric part of the layer name, or the original name if no number found
 */
const extractLayerNumber = (layerName: string): string => {
  // Try to extract number from patterns like "layer1", "layer2", "layer10", etc.
  const match = layerName.match(/layer(\d+)$/i);
  if (match && match[1]) {
    return match[1];
  }
  // If no match, return original name
  return layerName;
};

/**
 * Add layer flags to a command string after the filename
 * @param command - Command string (e.g., "nextdraw -L8 filename.svg --speed_pendown 30")
 * @param layerName - Layer name to add (null/undefined/empty to skip)
 * @returns Command string with layer flags added after filename
 */
export const addLayerFlags = (
  command: string,
  layerName: string | null | undefined
): string => {
  console.log("[addLayerFlags] Called with layerName:", layerName);
  console.log("[addLayerFlags] Command:", command);

  if (!layerName || typeof layerName !== "string" || layerName.trim() === "") {
    console.log(
      "[addLayerFlags] Layer name is empty/null, returning original command"
    );
    return command;
  }

  // Extract the layer number from the layer name (e.g., "layer1" -> "1")
  const layerNumber = extractLayerNumber(layerName.trim());
  console.log(
    "[addLayerFlags] Extracted layer number:",
    layerNumber,
    "from layer name:",
    layerName
  );

  // Split command into parts
  const parts = command.split(/\s+/);
  console.log("[addLayerFlags] Command parts:", parts);

  // Find the filename (first argument that doesn't start with '-' and comes after 'nextdraw' and optional model flag)
  let filenameIndex = -1;
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    // Skip 'nextdraw' and model flags like '-L8'
    if (part === "nextdraw" || /^-L\d+$/.test(part)) {
      continue;
    }
    // First non-flag argument should be the filename
    if (!part.startsWith("-")) {
      filenameIndex = i;
      console.log(
        "[addLayerFlags] Found filename at index:",
        filenameIndex,
        "filename:",
        part
      );
      break;
    }
  }

  if (filenameIndex === -1) {
    // No filename found, return original command
    console.log(
      "[addLayerFlags] No filename found, returning original command"
    );
    return command;
  }

  // Insert layer flags after filename: "--mode layers --layer <layer_number>"
  const layerFlags = ["--mode", "layers", "--layer", layerNumber];
  parts.splice(filenameIndex + 1, 0, ...layerFlags);
  console.log("[addLayerFlags] Inserted layer flags, new parts:", parts);

  const result = parts.join(" ");
  console.log("[addLayerFlags] Final command:", result);
  return result;
};

/**
 * Build a complete nextdraw plot command with model flag
 * @param filename - SVG filename to plot
 * @param settings - Plot settings
 * @returns Complete nextdraw command string
 */
export const buildPlotCommand = (
  filename: string,
  settings: {
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
  }
): string => {
  const parts = ["nextdraw", getFlag()].filter(Boolean);

  // Add filename
  parts.push(filename);

  // Add speed settings
  if (settings.s_down !== undefined) {
    parts.push("--speed_pendown", String(settings.s_down));
  }
  if (settings.s_up !== undefined) {
    parts.push("--speed_penup", String(settings.s_up));
  }

  // Add pen position settings (always include if they are valid numbers)
  // Note: 0 is a valid pen position, so we check for finite numbers, not truthy values
  const pDown = settings.p_down;
  const pUp = settings.p_up;
  if (pDown !== undefined && pDown !== null && Number.isFinite(Number(pDown))) {
    parts.push("--pen_pos_down", String(pDown));
  }
  if (pUp !== undefined && pUp !== null && Number.isFinite(Number(pUp))) {
    parts.push("--pen_pos_up", String(pUp));
  }

  // Add handling mode
  const handling = settings.handling;
  if (handling !== undefined && handling !== 5) {
    parts.push("--handling", String(handling));
    if (handling === 4 && settings.speed !== undefined) {
      parts.push("-s", String(settings.speed));
    }
  }

  // Add penlift
  if (
    settings.penlift !== undefined &&
    settings.penlift >= 1 &&
    settings.penlift <= 3
  ) {
    parts.push("--penlift", String(settings.penlift));
  }

  // Add no_homing flag
  if (settings.no_homing) {
    parts.push("--no_homing");
  }

  // Add progress flag
  parts.push("--progress");

  // Build the command string first
  let command = parts.join(" ");

  // Add layer flags after filename using the dedicated function
  console.log("[buildPlotCommand] Layer setting:", settings.layer);
  console.log("[buildPlotCommand] Layer type:", typeof settings.layer);
  console.log("[buildPlotCommand] Layer truthy check:", !!settings.layer);
  console.log("[buildPlotCommand] Layer length:", settings.layer?.length);

  // Check if layer is a non-empty string
  if (
    settings.layer &&
    typeof settings.layer === "string" &&
    settings.layer.trim() !== ""
  ) {
    console.log("[buildPlotCommand] Adding layer flags for:", settings.layer);
    command = addLayerFlags(command, settings.layer);
    console.log("[buildPlotCommand] Command after adding layer:", command);
  } else {
    console.log(
      "[buildPlotCommand] Skipping layer flags - layer is empty/null/undefined"
    );
  }

  return command;
};
