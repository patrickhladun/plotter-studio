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

  if (import.meta.env?.DEV) {
    // During `pnpm dev` the dashboard runs on its own port, so talk to the API fallback port.
    return FALLBACK_BASE_URL;
  }

  return window.location.origin;
};

export const API_BASE_URL = inferBaseUrl();
