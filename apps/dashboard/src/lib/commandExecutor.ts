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
  const isDev = import.meta.env?.DEV;

  // Always show command in toaster
  showCommandToast(label, command);

  // In dev mode, don't send to API
  if (isDev) {
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
  try {
    const formData = new FormData();
    formData.append('command', command);

    const response = await fetch(`${API_BASE_URL}/plot`, {
      method: 'POST',
      body: formData,
    });

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
    return {
      success: false,
      payload: null,
      error: errorMessage,
    };
  }
}

