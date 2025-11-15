import { API_BASE_URL } from './rpiApi';
import { showCommandToast } from './toastStore';

type CommandPayload = {
  ok?: boolean;
  command?: string;
  stdout?: string;
  stderr?: string;
  detail?: unknown;
  state?: string;
};

/**
 * Execute a command. In dev mode, only shows the command in toaster.
 * In production, sends to API and shows command in toaster.
 */
export async function executeCommand(
  command: string,
  label: string
): Promise<{ success: boolean; payload: CommandPayload | null; error?: string }> {
  // Check if we're in dev mode - use PROD flag (inverted) or MODE check
  // In Vite: DEV=true in dev, PROD=true in production, MODE='development' or 'production'
  const isDev = import.meta.env?.DEV === true || import.meta.env?.MODE === 'development';
  const isProd = import.meta.env?.PROD === true || import.meta.env?.MODE === 'production';
  
  // Log environment info for debugging
  if (typeof window !== 'undefined') {
    console.log('[commandExecutor] Environment:', {
      DEV: import.meta.env?.DEV,
      PROD: import.meta.env?.PROD,
      MODE: import.meta.env?.MODE,
      isDev,
      isProd,
      API_BASE_URL,
    });
  }

  // Always show command in toaster
  showCommandToast(label, command);

  // In dev mode, don't send to API
  if (isDev && !isProd) {
    console.log(`[DEV MODE] Would execute: ${command}`);
    return {
      success: true,
      payload: {
        ok: true,
        command,
        stdout: '[DEV MODE] Command not executed',
      },
    };
  }

  // In production, send to API
  console.log(`[commandExecutor] Sending command to API: ${API_BASE_URL}/plot`);
  console.log(`[commandExecutor] Command: ${command}`);
  
  try {
    const formData = new FormData();
    formData.append('command', command);

    const url = `${API_BASE_URL}/plot`;
    console.log(`[commandExecutor] Fetching: ${url}`);
    
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });
    
    console.log(`[commandExecutor] Response status: ${response.status} ${response.statusText}`);

    const text = await response.text();
    let payload: CommandPayload | null = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch (parseError) {
      payload = null;
    }

    if (!response.ok) {
      const message =
        typeof payload?.detail === 'string'
          ? payload.detail
          : text || 'Command execution failed';
      return {
        success: false,
        payload,
        error: message,
      };
    }

    if (payload && payload.ok === false) {
      const stdout = typeof payload.stdout === 'string' ? payload.stdout.trim() : '';
      const stderr = typeof payload.stderr === 'string' ? payload.stderr.trim() : '';
      const message = stderr || stdout || 'Command failed';
      return {
        success: false,
        payload,
        error: message,
      };
    }

    return {
      success: true,
      payload,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('[commandExecutor] Error executing command:', error);
    console.error('[commandExecutor] Error details:', {
      message: errorMessage,
      stack: error instanceof Error ? error.stack : undefined,
      url: `${API_BASE_URL}/plot`,
    });
    return {
      success: false,
      payload: null,
      error: errorMessage,
    };
  }
}

