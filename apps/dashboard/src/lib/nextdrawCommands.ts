/**
 * Plotter model mapping and command building utilities
 */

// Mapping from model numbers to model names (for display)
export const NEXTDRAW_MODEL_MAP: Record<number, string> = {
  1: "AxiDraw V2, V3, or SE/A4",
  2: "AxiDraw V3/A3 or SE/A3",
  3: "AxiDraw V3 XLX",
  4: "AxiDraw MiniKit",
  5: "AxiDraw SE/A1",
  6: "AxiDraw SE/A2",
  7: "AxiDraw V3/B6",
  8: "Bantam Tools NextDraw™ 8511 (Default)",
  9: "Bantam Tools NextDraw™ 1117",
  10: "Bantam Tools NextDraw™ 2234",
};

// Array of model numbers (for iteration)
export const NEXTDRAW_MODEL_NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as const;

// Array of model names (for backward compatibility and display)
export const NEXTDRAW_MODELS = NEXTDRAW_MODEL_NUMBERS.map(
  (num) => NEXTDRAW_MODEL_MAP[num]
) as readonly string[];

// Default model number
export const DEFAULT_MODEL_NUMBER = 8;

/**
 * Get model name from model number (for display)
 */
export function getModelName(modelNumber: number | null | undefined): string {
  if (modelNumber === null || modelNumber === undefined) {
    return NEXTDRAW_MODEL_MAP[DEFAULT_MODEL_NUMBER];
  }
  return (
    NEXTDRAW_MODEL_MAP[modelNumber] || NEXTDRAW_MODEL_MAP[DEFAULT_MODEL_NUMBER]
  );
}

/**
 * Get model number from model number or string (for backward compatibility)
 * This function accepts both numbers and strings, but always returns a number
 */
export function getModelNumber(
  model: number | string | null | undefined
): number | null {
  if (model === null || model === undefined) {
    return null;
  }
  // If it's already a number, return it (validate range)
  if (typeof model === "number") {
    if (model >= 1 && model <= 10) {
      return model;
    }
    console.warn(
      `Invalid model number ${model}, defaulting to ${DEFAULT_MODEL_NUMBER}`
    );
    return DEFAULT_MODEL_NUMBER;
  }
  // If it's a string, try to parse it as a number
  if (typeof model === "string") {
    const modelNum = parseInt(model, 10);
    if (!isNaN(modelNum) && modelNum >= 1 && modelNum <= 10) {
      return modelNum;
    }
    // Try to find by name (backward compatibility)
    for (const [num, name] of Object.entries(NEXTDRAW_MODEL_MAP)) {
      if (name === model) {
        return parseInt(num, 10);
      }
    }
    console.warn(
      `Unknown Plotter model '${model}', defaulting to model ${DEFAULT_MODEL_NUMBER}`
    );
    return DEFAULT_MODEL_NUMBER;
  }
  return DEFAULT_MODEL_NUMBER;
}

/**
 * Get model flag string (e.g., "-L8") for use in command building
 * Returns empty string if no model is provided
 * @param model - Model number or string
 * @returns Model flag string like "-L8" or empty string
 */
export function getModelFlag(
  model: number | string | null | undefined
): string {
  const modelNumber = getModelNumber(model);
  if (modelNumber === null) {
    return "";
  }
  return `-L${modelNumber}`;
}

/**
 * Build a complete nextdraw command with model flag
 */
export function buildNextdrawCommand(
  model: number | string | null | undefined,
  ...args: string[]
): string {
  const parts: string[] = ["nextdraw"];

  // Add model flag if model is provided
  const modelNumber = getModelNumber(model);
  if (modelNumber !== null) {
    parts.push(`-L${modelNumber}`);
  }

  // Add remaining arguments
  parts.push(...args);

  return parts.join(" ");
}

/**
 * Build a utility command (e.g., toggle, enable_xy, disable_xy, walk_home)
 * @param model - Model number to include -L flag. If null/undefined, no model flag is added.
 */
export function buildUtilityCommand(
  model: number | string | null | undefined,
  command: string
): string {
  return buildNextdrawCommand(model, "-m", "utility", "-M", command);
}
