const FALLBACK_BASE_URL = "http://localhost:2222";

const inferBaseUrl = (): string => {
  if (typeof window === "undefined") {
    return FALLBACK_BASE_URL;
  }

  const override =
    (
      window as {
        __PLOTTERSTUDIO_API_BASE__?: string;
        __SYNTHDRAW_API_BASE__?: string;
      }
    ).__PLOTTERSTUDIO_API_BASE__ ||
    (window as { __SYNTHDRAW_API_BASE__?: string }).__SYNTHDRAW_API_BASE__;
  if (override) {
    return override;
  }

  const envOverride = import.meta.env?.VITE_API_BASE_URL;
  if (typeof envOverride === "string" && envOverride.trim().length > 0) {
    return envOverride.trim();
  }

  // Check if we're in dev mode (Vite dev server)
  const isDev =
    import.meta.env?.DEV === true || import.meta.env?.MODE === "development";
  const isProd =
    import.meta.env?.PROD === true || import.meta.env?.MODE === "production";

  // In dev mode, always use relative paths to leverage Vite proxy
  // This avoids CORS issues and works for both localhost and network access
  if (isDev && !isProd) {
    return "";
  }

  // Production mode: if dashboard is on port 3131, API is on port 3333
  // Use the same hostname as the dashboard (works for both localhost and network IPs)
  // IMPORTANT: Use window.location at runtime, not at module load time
  const fullLocation = window.location.href;
  const currentPort = window.location.port;
  const currentHostname = window.location.hostname;
  const currentProtocol = window.location.protocol;
  const currentHost = window.location.host; // includes port

  // Log all location info for debugging
  console.log("[rpiApi] Window location info:", {
    href: fullLocation,
    hostname: currentHostname,
    port: currentPort,
    protocol: currentProtocol,
    host: currentHost,
    origin: window.location.origin,
  });

  // Check if we're on production port (3131) or if the URL contains port 3131
  const isProductionPort =
    currentPort === "3131" ||
    currentHost.includes(":3131") ||
    fullLocation.includes(":3131");

  if (isProductionPort) {
    // Extract hostname from the actual URL - this is the most reliable way
    let apiHostname = currentHostname;

    // ALWAYS try to extract IP from the full URL first - this is most reliable
    const ipMatch = fullLocation.match(/https?:\/\/(\d+\.\d+\.\d+\.\d+)/);
    if (ipMatch && ipMatch[1]) {
      apiHostname = ipMatch[1];
      console.log("[rpiApi] Extracted IP from URL:", apiHostname);
    } else if (
      currentHostname === "localhost" ||
      currentHostname === "127.0.0.1"
    ) {
      // If we still have localhost, this is a problem
      console.error(
        "[rpiApi] ERROR: Cannot determine network IP! Using localhost which will not work from network devices."
      );
      console.error("[rpiApi] Full location:", fullLocation);
      console.error(
        "[rpiApi] Please ensure you're accessing via network IP (e.g., http://192.168.1.37:3131)"
      );
    }

    const apiUrl = `${currentProtocol}//${apiHostname}:3333`;
    console.log("[rpiApi] Production mode detected - using API URL:", apiUrl);
    return apiUrl;
  }

  // Default: use same origin (for production when ports match or other scenarios)
  return window.location.origin;
};

// Export as a getter function to ensure it's evaluated at runtime
export const getApiBaseUrl = (): string => inferBaseUrl();

// For backward compatibility, also export as a constant (but it will be evaluated at module load)
// In production, this should still work because window.location is available
export const API_BASE_URL = inferBaseUrl();

// Debug logging
if (typeof window !== "undefined") {
  const isDev = import.meta.env?.DEV;
  const isProd = import.meta.env?.PROD;
  console.log("[rpiApi] Environment:", {
    DEV: isDev,
    PROD: isProd,
    MODE: import.meta.env?.MODE,
    API_BASE_URL: API_BASE_URL || "(empty - using proxy)",
    windowLocation: `${window.location.protocol}//${window.location.hostname}:${window.location.port}`,
  });
}
