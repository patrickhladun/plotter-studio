const FALLBACK_BASE_URL = 'http://localhost:2222';

const inferBaseUrl = (): string => {
  if (typeof window === 'undefined') {
    return FALLBACK_BASE_URL;
  }

  const override = (window as {
    __PLOTTERSTUDIO_API_BASE__?: string;
    __SYNTHDRAW_API_BASE__?: string;
  }).__PLOTTERSTUDIO_API_BASE__ || (window as { __SYNTHDRAW_API_BASE__?: string }).__SYNTHDRAW_API_BASE__;
  if (override) {
    return override;
  }

  const envOverride = import.meta.env?.VITE_API_BASE_URL;
  if (typeof envOverride === 'string' && envOverride.trim().length > 0) {
    return envOverride.trim();
  }

  // Check if we're in dev mode (Vite dev server)
  const isDev = import.meta.env?.DEV === true || import.meta.env?.MODE === 'development';
  const isProd = import.meta.env?.PROD === true || import.meta.env?.MODE === 'production';
  
  // In dev mode, always use relative paths to leverage Vite proxy
  // This avoids CORS issues and works for both localhost and network access
  if (isDev && !isProd) {
    return '';
  }

  // Production mode: if dashboard is on port 3131, API is on port 3333
  // Use the same hostname as the dashboard (works for both localhost and network IPs)
  // IMPORTANT: Use window.location at runtime, not at module load time
  const currentPort = window.location.port;
  const currentHostname = window.location.hostname;
  const currentProtocol = window.location.protocol;
  
  if (currentPort === '3131') {
    const apiUrl = `${currentProtocol}//${currentHostname}:3333`;
    console.log('[rpiApi] Production mode detected:', {
      port: currentPort,
      hostname: currentHostname,
      protocol: currentProtocol,
      apiUrl,
    });
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
if (typeof window !== 'undefined') {
  const isDev = import.meta.env?.DEV;
  const isProd = import.meta.env?.PROD;
  console.log('[rpiApi] Environment:', {
    DEV: isDev,
    PROD: isProd,
    MODE: import.meta.env?.MODE,
    API_BASE_URL: API_BASE_URL || '(empty - using proxy)',
    windowLocation: `${window.location.protocol}//${window.location.hostname}:${window.location.port}`,
  });
}
