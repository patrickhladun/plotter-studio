import { API_BASE_URL } from './rpiApi';

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
};

export type DeviceSettings = {
  host?: string | null;
  port?: number | null;
  axicli_path?: string | null;
  home_offset_x?: number;
  home_offset_y?: number;
  notes?: string | null;
  penlift?: number;
  no_homing?: boolean;
  nextdraw_model?: string | null;
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
  'Content-Type': 'application/json',
};

const buildUrl = (path: string) => `${API_BASE_URL}${path}`;

const encode = (value: string) => encodeURIComponent(value);

type Parser = 'json' | 'text' | 'void';

async function request<T>(path: string, init: RequestInit = {}, parser: Parser = 'json'): Promise<T> {
  const response = await fetch(buildUrl(path), init);
  const body = await response.text();

  if (!response.ok) {
    let message = body || response.statusText || 'Request failed';
    if (body) {
      try {
        const data = JSON.parse(body);
        if (typeof data === 'string') {
          message = data;
        } else if (data?.detail) {
          message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        }
      } catch {
        // ignore parse errors
      }
    }
    throw new Error(message);
  }

  if (parser === 'void') {
    return undefined as T;
  }
  if (parser === 'text') {
    return body as T;
  }
  if (!body) {
    return {} as T;
  }
  try {
    return JSON.parse(body) as T;
  } catch {
    const trimmed = body.trim();
    throw new Error(trimmed || 'Invalid JSON response from server');
  }
}

export const filesApi = {
  list: () => request<FileMeta[]>('/files'),
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<FileMeta>('/files', { method: 'POST', body: formData });
  },
  remove: (filename: string) =>
    request<void>(`/files/${encode(filename)}`, { method: 'DELETE' }, 'void'),
  rename: (filename: string, newName: string) =>
    request<FileMeta>(`/files/${encode(filename)}/rename`, {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ new_name: newName }),
    }),
  rotate: (filename: string, angle: number) =>
    request<{ rotated: boolean; angle: number }>(`/files/${encode(filename)}/rotate`, {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ angle }),
    }),
  raw: (filename: string) => request<string>(`/files/${encode(filename)}/raw`, {}, 'text'),
  preview: (
    filename: string,
    options: { handling: number; speed: number; penlift?: number; model?: string | null }
  ) => {
    const params = new URLSearchParams({
      handling: String(options.handling),
      speed: String(options.speed),
      penlift: String(options.penlift ?? 1),
    });
    if (options.model) {
      params.set('model', options.model);
    }
    return request<PreviewMetrics>(`/files/${encode(filename)}/preview?${params.toString()}`);
  },
  plot: (filename: string, payload: PlotSettings) =>
    request<PlotStartResponse>(`/files/${encode(filename)}/plot`, {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    }),
  cancelPlot: () => request<{ ok?: boolean; message?: string }>('/plot/cancel', { method: 'POST' }),
  status: () => request<PlotStatusResponse>('/plot/status'),
};
