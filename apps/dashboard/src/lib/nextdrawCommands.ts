/**
 * NextDraw model mapping and command building utilities
 */

export const NEXTDRAW_MODELS = [
  "AxiDraw V2, V3, or SE/A4",
  "AxiDraw V3/A3 or SE/A3",
  "AxiDraw V3 XLX",
  "AxiDraw MiniKit",
  "AxiDraw SE/A1",
  "AxiDraw SE/A2",
  "AxiDraw V3/B6",
  "Bantam Tools NextDraw™ 8511 (Default)",
  "Bantam Tools NextDraw™ 1117",
  "Bantam Tools NextDraw™ 2234",
] as const;

// Mapping from NextDraw model names to model numbers for -L flag
const NEXTDRAW_MODEL_MAP: Record<string, number> = {
  "AxiDraw V2, V3, or SE/A4": 1,
  "AxiDraw V3/A3 or SE/A3": 2,
  "AxiDraw V3 XLX": 3,
  "AxiDraw MiniKit": 4,
  "AxiDraw SE/A1": 5,
  "AxiDraw SE/A2": 6,
  "AxiDraw V3/B6": 7,
  "Bantam Tools NextDraw™ 8511 (Default)": 8,
  "Bantam Tools NextDraw™ 1117": 9,
  "Bantam Tools NextDraw™ 2234": 10,
};

/**
 * Convert NextDraw model name to model number for -L flag
 */
export function getModelNumber(
  modelName: string | null | undefined
): number | null {
  if (!modelName) {
    return null;
  }
  // Check exact match first
  if (modelName in NEXTDRAW_MODEL_MAP) {
    return NEXTDRAW_MODEL_MAP[modelName];
  }
  // Check if it's already a number (as string)
  const modelNum = parseInt(modelName, 10);
  if (!isNaN(modelNum) && modelNum >= 1 && modelNum <= 10) {
    return modelNum;
  }
  // Default to model 8 (Bantam Tools NextDraw™ 8511) if not found
  console.warn(`Unknown NextDraw model '${modelName}', defaulting to model 8`);
  return 8;
}

/**
 * Build a complete nextdraw command with model flag
 */
export function buildNextdrawCommand(
  model: string | null | undefined,
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
 * @param model - Optional model to include -L flag. If null/undefined, no model flag is added.
 */
export function buildUtilityCommand(
  model: string | null | undefined,
  command: string
): string {
  return buildNextdrawCommand(model, "-m", "utility", "-M", command);
}

/**
 * Build a utility command without model flag (e.g., walk_home)
 */
export function buildUtilityCommandWithoutModel(command: string): string {
  return buildNextdrawCommand(null, "-m", "utility", "-M", command);
}

/**
 * Build a manual command (e.g., walk with coordinates, raise_pen)
 */
export function buildManualCommand(
  model: string | null | undefined,
  command: string
): string {
  return buildNextdrawCommand(
    model,
    "--mode",
    "manual",
    "--manual_cmd",
    command
  );
}
