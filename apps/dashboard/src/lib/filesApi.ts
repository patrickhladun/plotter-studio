import { API_BASE_URL } from "./rpiApi";

export type FileMeta = {
  name: string;
  size: number;
  updated_at: string;
  width?: string | null;
  height?: string | null;
  viewBox?: string | null;
};

export type PreviewMetrics = {
  estimated_seconds: number | null;
  distance_mm: number | null;
};

export type PlotStatusResponse = {
  running?: boolean;
  file?: string | null;
  progress?: number | null;
  elapsed_seconds?: number | null;
  distance_mm?: number | null;
  error?: string | null;
};

export type PlotSettings = {
  page: string;
  s_down: number;
  s_up: number;
  p_down: number;
  p_up: number;
  handling: number;
  speed: number;
  brushless?: boolean;
  penlift?: number;
  no_homing?: boolean;
  model?: string | null;
  layer?: string | null;
};

export type DeviceSettings = {
  axicli_path?: string | null;
  home_offset_x?: number;
  home_offset_y?: number;
  notes?: string | null;
  penlift?: number;
  no_homing?: boolean;
  nextdraw_model?: string | null;
};

export type DeviceConfig = {
  selectedDeviceProfile?: string | null;
  defaultDeviceOverride?: DeviceSettings | null;
  customPresets?: Record<string, DeviceSettings> | null;
};

export type PlotStartResponse = {
  ok?: boolean;
  pid?: number;
  file?: string;
  cmd?: string;
  page?: string;
  completed?: boolean;
  output?: string;
};

const jsonHeaders = {
  "Content-Type": "application/json",
};

const buildUrl = (path: string) => `${API_BASE_URL}${path}`;

const encode = (value: string) => encodeURIComponent(value);

type Parser = "json" | "text" | "void";

async function request<T>(
  path: string,
  init: RequestInit = {},
  parser: Parser = "json"
): Promise<T> {
  const url = buildUrl(path);
  const isDev = import.meta.env?.DEV;

  // Don't set Content-Type for FormData - browser will set it with boundary
  const headers = init.headers;
  const isFormData = init.body instanceof FormData;

  // Add timeout for requests (30 seconds)
  const timeoutMs = 30000;
  const controller = new AbortController();
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  // Only set timeout if no signal is already provided
  if (!init.signal) {
    timeoutId = setTimeout(() => {
      if (!controller.signal.aborted) {
        if (isDev) {
          console.warn(
            `[filesApi] Request timeout after ${timeoutMs}ms: ${url}`
          );
        }
        controller.abort();
      }
    }, timeoutMs);
  }

  const finalInit: RequestInit = {
    ...init,
    headers: isFormData ? undefined : headers,
    signal: init.signal || controller.signal,
  };

  if (isDev) {
    console.log(`[filesApi] ${init.method || "GET"} ${url}`, {
      isFormData,
      bodyType: init.body instanceof FormData ? "FormData" : typeof init.body,
      hasHeaders: !!init.headers,
      hasSignal: !!finalInit.signal,
    });
  }

  try {
    if (isDev) {
      console.log(`[filesApi] Fetching: ${url}`, {
        method: finalInit.method || "GET",
        hasBody: !!finalInit.body,
        signal: !!finalInit.signal,
      });
    }

    const fetchStartTime = Date.now();
    const response = await fetch(url, finalInit);
    const fetchDuration = Date.now() - fetchStartTime;

    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    if (isDev) {
      console.log(
        `[filesApi] Response received (${fetchDuration}ms): ${response.status} ${response.statusText}`,
        {
          url,
          ok: response.ok,
          contentType: response.headers.get("content-type"),
          headers: Object.fromEntries(response.headers.entries()),
        }
      );
    }

    const body = await response.text();

    if (!response.ok) {
      let message = body || response.statusText || "Request failed";
      if (body) {
        try {
          const data = JSON.parse(body);
          if (typeof data === "string") {
            message = data;
          } else if (data?.detail) {
            message =
              typeof data.detail === "string"
                ? data.detail
                : JSON.stringify(data.detail);
          }
        } catch {
          // ignore parse errors
        }
      }
      const error = new Error(message);
      (error as any).status = response.status;
      (error as any).url = url;
      throw error;
    }

    if (parser === "void") {
      return undefined as T;
    }
    if (parser === "text") {
      return body as T;
    }
    if (!body) {
      return {} as T;
    }
    try {
      return JSON.parse(body) as T;
    } catch {
      const trimmed = body.trim();
      const error = new Error(trimmed || "Invalid JSON response from server");
      (error as any).url = url;
      throw error;
    }
  } catch (error) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    // Enhanced error logging
    if (isDev) {
      const errorDetails: any = {
        error,
        errorName: error instanceof Error ? error.name : typeof error,
        errorMessage: error instanceof Error ? error.message : String(error),
        isAborted: error instanceof Error && error.name === "AbortError",
        signalAborted: controller.signal.aborted,
        url,
        method: init.method || "GET",
      };

      if (error instanceof TypeError && error.message.includes("fetch")) {
        errorDetails.networkError = true;
        errorDetails.suggestion =
          "API server may not be running. Check if http://localhost:2222/status is accessible.";
      }

      console.error(
        `[filesApi] Request failed: ${init.method || "GET"} ${url}`,
        errorDetails
      );
    }

    // Create a new error to avoid modifying read-only properties
    let finalError: Error;
    if (error instanceof Error) {
      if (error.name === "AbortError") {
        finalError = new Error(`Request timeout after ${timeoutMs}ms: ${url}`);
        finalError.name = "AbortError";
        (finalError as any).isTimeout = true;
        (finalError as any).url = url;
        (finalError as any).status = undefined;
      } else {
        finalError = new Error(error.message || "Request failed");
        finalError.name = error.name;
        (finalError as any).url = url;
        (finalError as any).status = (error as any).status;
      }
    } else {
      finalError = new Error(String(error));
      (finalError as any).url = url;
    }

    throw finalError;
  }
}

export const filesApi = {
  list: () => request<FileMeta[]>("/files"),
  upload: (file: File) => {
    if (import.meta.env?.DEV) {
      console.log("[filesApi] Starting upload:", {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type,
        apiBaseUrl: API_BASE_URL || "(empty - using proxy)",
      });
    }
    const formData = new FormData();
    formData.append("file", file);
    return request<FileMeta>("/files", { method: "POST", body: formData });
  },
  remove: (filename: string) =>
    request<void>(`/files/${encode(filename)}`, { method: "DELETE" }, "void"),
  rename: (filename: string, newName: string) =>
    request<FileMeta>(`/files/${encode(filename)}/rename`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ new_name: newName }),
    }),
  rotate: (filename: string, angle: number) =>
    request<{ rotated: boolean; angle: number }>(
      `/files/${encode(filename)}/rotate`,
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ angle }),
      }
    ),
  raw: (filename: string) =>
    request<string>(`/files/${encode(filename)}/raw`, {}, "text"),
  getLayers: (filename: string) =>
    request<{ layers: string[] }>(`/files/${encode(filename)}/layers`),
  preview: (
    filename: string,
    options: {
      handling: number;
      speed: number;
      penlift?: number;
      model?: string | null;
    }
  ) => {
    const params = new URLSearchParams({
      handling: String(options.handling),
      speed: String(options.speed),
      penlift: String(options.penlift ?? 1),
    });
    if (options.model) {
      params.set("model", options.model);
    }
    return request<PreviewMetrics>(
      `/files/${encode(filename)}/preview?${params.toString()}`
    );
  },
  plot: (filename: string, payload: PlotSettings) =>
    request<PlotStartResponse>(`/files/${encode(filename)}/plot`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    }),
  cancelPlot: () =>
    request<{ ok?: boolean; message?: string }>("/plot/cancel", {
      method: "POST",
    }),
  status: () => request<PlotStatusResponse>("/plot/status"),
  // Settings API - stores data on server in JSON files
  getDevicePresets: () =>
    request<Record<string, DeviceSettings>>("/settings/device-presets"),
  saveDevicePresets: (presets: Record<string, DeviceSettings>) =>
    request<{ ok?: boolean; message?: string }>("/settings/device-presets", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(presets),
    }),
  getPrintPresets: () =>
    request<Record<string, PlotSettings>>("/settings/print-presets"),
  savePrintPresets: (presets: Record<string, PlotSettings>) =>
    request<{ ok?: boolean; message?: string }>("/settings/print-presets", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(presets),
    }),
  getSelectedProfiles: () =>
    request<{ deviceProfile?: string | null; printProfile?: string | null }>(
      "/settings/selected-profiles"
    ),
  saveSelectedProfiles: (profiles: {
    deviceProfile?: string | null;
    printProfile?: string | null;
  }) =>
    request<{ ok?: boolean; message?: string }>("/settings/selected-profiles", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(profiles),
    }),
  getSessionState: () =>
    request<{
      selected_file?: string | null;
      selected_layer?: string | null;
      last_updated?: number | null;
    }>("/session/state"),
  updateSessionState: (state: {
    selected_file?: string | null;
    selected_layer?: string | null;
  }) =>
    request<{ ok?: boolean; message?: string }>("/session/state", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(state),
    }),
  // Debug helper to test API connectivity
  testConnection: async () => {
    console.log("[filesApi] Testing API connection...");
    console.log(
      "[filesApi] API_BASE_URL:",
      API_BASE_URL || "(empty - using proxy)"
    );
    console.log("[filesApi] Full URL would be:", buildUrl("/status"));

    try {
      // Test with a simple fetch first
      const testUrl = buildUrl("/status");
      console.log("[filesApi] Attempting direct fetch to:", testUrl);

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(testUrl, { signal: controller.signal });
      clearTimeout(timeout);

      console.log("[filesApi] Direct fetch response:", {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
      });

      const text = await response.text();
      console.log("[filesApi] Response body:", text);

      const result = JSON.parse(text);
      console.log("[filesApi] API connection test successful:", result);
      return {
        success: true,
        result,
        response: { status: response.status, statusText: response.statusText },
      };
    } catch (error) {
      console.error("[filesApi] API connection test failed:", error);
      const errorInfo =
        error instanceof Error
          ? {
              name: error.name,
              message: error.message,
              stack: error.stack,
            }
          : error;
      return { success: false, error: errorInfo, url: buildUrl("/status") };
    }
  },
};

// Expose debug helpers in dev mode
if (import.meta.env?.DEV && typeof window !== "undefined") {
  (window as any).__PLOTTERSTUDIO_DEBUG__ = {
    filesApi,
    API_BASE_URL,
    testConnection: () => filesApi.testConnection(),
    viewLogs: async (lines = 50) => {
      try {
        const response = await fetch(
          buildUrl("/debug/logs") + `?lines=${lines}`
        );
        const data = await response.json();
        if (data.error) {
          console.error("[Debug] Error fetching logs:", data.error);
          return data;
        }
        console.log(
          `[Debug] Recent ${data.returned_lines} of ${data.total_lines} log lines:`
        );
        console.log(data.logs.join(""));
        return data;
      } catch (error) {
        console.error("[Debug] Failed to fetch logs:", error);
        return { error: String(error) };
      }
    },
  };
  console.log(
    "[filesApi] Debug helpers available at window.__PLOTTERSTUDIO_DEBUG__"
  );
  console.log(
    "[filesApi] Use window.__PLOTTERSTUDIO_DEBUG__.viewLogs() to see API server logs"
  );
}
