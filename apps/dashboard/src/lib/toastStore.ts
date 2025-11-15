import { writable } from 'svelte/store';

export type ToastTone = 'info' | 'success' | 'error';

export type Toast = {
  id: number;
  message: string;
  detail?: string;
  tone: ToastTone;
  createdAt: number;
};

const store = writable<Toast[]>([]);
let counter = 0;

export const toasts = {
  subscribe: store.subscribe,
};

export const dismissToast = (id: number) => {
  store.update((items) => items.filter((toast) => toast.id !== id));
};

type ToastOptions = {
  detail?: string;
  tone?: ToastTone;
  duration?: number;
};

export const pushToast = (message: string, options?: ToastOptions) => {
  const id = ++counter;
  const toast: Toast = {
    id,
    message,
    detail: options?.detail,
    tone: options?.tone ?? 'info',
    createdAt: Date.now(),
  };
  store.update((items) => [...items, toast]);
  const duration = options?.duration ?? 6000;
  if (duration > 0) {
    setTimeout(() => dismissToast(id), duration);
  }
  return id;
};

const stripUrlFromCommand = (text: string) => {
  try {
    const url = new URL(text);
    return url.pathname + url.search + url.hash;
  } catch {
    return text;
  }
};

const trimExecutablePath = (text: string) => {
  const trimmed = text.trim();
  if (!trimmed) {
    return trimmed;
  }
  const firstSpace = trimmed.indexOf(' ');
  const head = firstSpace === -1 ? trimmed : trimmed.slice(0, firstSpace);
  const tail = firstSpace === -1 ? '' : trimmed.slice(firstSpace);
  const executable = head.replace(/^.*[\\/]/, '');
  return `${executable}${tail}`;
};

const stripSvgPath = (text: string) =>
  text.replace(/([^\s"']+\.svg)/gi, (match) => match.replace(/^.*[\\/]/, ''));

export const showCommandToast = (label: string, command?: string | null) => {
  if (!command) {
    return;
  }
  pushToast(label, {
    detail: stripSvgPath(trimExecutablePath(stripUrlFromCommand(command))),
    tone: 'info',
    duration: 8000,
  });
};
