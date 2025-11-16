const FALLBACK_BASE_URL = 'http://localhost:2222';

const inferBaseUrl = () => {
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
  if (window.location.port === '3131') {
    const apiUrl = `${window.location.protocol}//${window.location.hostname}:3333`;
    console.log('[rpiApi] Production mode detected - using API URL:', apiUrl);
    return apiUrl;
  }

  // Default: use same origin (for production when ports match or other scenarios)
  return window.location.origin;
};

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
