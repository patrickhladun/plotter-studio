<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { API_BASE_URL } from '../../lib/rpiApi';

  let xInput: string | number | null = '';
  let yInput: string | number | null = '';
  let isMoving = false;
  let penBusy = false;
  let statusMessage: string | null = null;
  let statusTone: 'success' | 'error' | null = null;
  let motorsBusy = false;

  const setStatus = (message: string, tone: 'success' | 'error') => {
    statusMessage = message;
    statusTone = tone;
  };

  const clearStatus = () => {
    statusMessage = null;
    statusTone = null;
  };

  const handlePenToggle = async () => {
    clearStatus();
    try {
      penBusy = true;
      const response = await fetch(`${API_BASE_URL}/pen/toggle`, { method: 'POST' });
      const text = await response.text();
      if (!response.ok) {
        console.error('API error:', response.statusText);
        let message = text || 'Failed to toggle pen';
        try {
          const payload = JSON.parse(text);
          if (payload?.detail) {
            message = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
          }
        } catch (parseError) {
          // ignore parse error, fall back to text
        }
        setStatus(message, 'error');
        return;
      }

      let payload: Record<string, unknown> | null = null;
      try {
        payload = text ? JSON.parse(text) : null;
      } catch (parseError) {
        payload = null;
      }

      const state = payload && typeof payload.state === 'string' ? payload.state : null;
      const stdout = payload && typeof payload.stdout === 'string' ? payload.stdout : null;
      const inferredMessage = state
        ? `Pen ${state}`
        : stdout && stdout.trim().length > 0
          ? stdout.trim().split('\n')[0]
          : 'Pen toggled';
      setStatus(inferredMessage, 'success');
    } catch (error) {
      console.error('API error:', error);
      setStatus('Pen toggle failed', 'error');
    } finally {
      penBusy = false;
    }
  };

  const handleMotors = async (enable: boolean) => {
    clearStatus();
    try {
      motorsBusy = true;
      const endpoint = enable ? 'enable_motors' : 'disable_motors';
      const response = await fetch(`${API_BASE_URL}/${endpoint}`, { method: 'POST' });
      const text = await response.text();
      if (!response.ok) {
        console.error('API error:', response.statusText);
        let message = text || `Failed to ${enable ? 'enable' : 'disable'} motors`;
        try {
          const payload = JSON.parse(text);
          if (payload?.detail) {
            message = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
          }
        } catch (parseError) {
          // ignore parse errors
        }
        setStatus(message, 'error');
        return;
      }

      let payload: Record<string, unknown> | null = null;
      try {
        payload = text ? JSON.parse(text) : null;
      } catch (parseError) {
        payload = null;
      }

      const stdout = payload && typeof payload.stdout === 'string' ? payload.stdout : null;
      const inferred = stdout && stdout.trim().length > 0
        ? stdout.trim().split('\n')[0]
        : enable
          ? 'Motors enabled'
          : 'Motors disabled';
      setStatus(inferred, 'success');
    } catch (error) {
      console.error('API error:', error);
      setStatus(`Motor ${enable ? 'enable' : 'disable'} failed`, 'error');
    } finally {
      motorsBusy = false;
    }
  };

  const handleMove = async () => {
    clearStatus();
    const normalizedX =
      typeof xInput === 'number'
        ? xInput.toString()
        : typeof xInput === 'string'
          ? xInput.trim()
          : '';
    const normalizedY =
      typeof yInput === 'number'
        ? yInput.toString()
        : typeof yInput === 'string'
          ? yInput.trim()
          : '';

    if (!normalizedX && !normalizedY) {
      setStatus('Enter at least one coordinate in millimeters.', 'error');
      return;
    }

    const xValue = normalizedX ? Number(normalizedX) : 0;
    const yValue = normalizedY ? Number(normalizedY) : 0;

    if (Number.isNaN(xValue) || Number.isNaN(yValue)) {
      setStatus('Coordinates must be numbers.', 'error');
      return;
    }

    const params = new URLSearchParams();
    params.set('x_mm', xValue.toString());
    params.set('y_mm', yValue.toString());

    try {
      isMoving = true;
      const response = await fetch(`${API_BASE_URL}/walk`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params.toString(),
      });

      if (!response.ok) {
        console.error('API error:', response.statusText);
        setStatus('Move command failed', 'error');
        return;
      }

      setStatus(`Walking to offset (Δx=${xValue}, Δy=${yValue})`, 'success');
    } catch (error) {
      console.error('API error:', error);
      setStatus('Move request failed', 'error');
    } finally {
      isMoving = false;
    }
  };

  const handleWalkHome = async () => {
    clearStatus();
    try {
      isMoving = true;
      const response = await fetch(`${API_BASE_URL}/walk_home`, { method: 'POST' });
      const text = await response.text();
      if (!response.ok) {
        console.error('API error:', response.statusText);
        let message = text || 'Walk home failed';
        try {
          const payload = JSON.parse(text);
          if (payload?.detail) {
            message = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
          }
        } catch (parseError) {
          // ignore parse errors
        }
        setStatus(message, 'error');
        return;
      }

      let payload: Record<string, unknown> | null = null;
      try {
        payload = text ? JSON.parse(text) : null;
      } catch (parseError) {
        payload = null;
      }

      const stdout = payload && typeof payload.stdout === 'string' ? payload.stdout : null;
      const inferred = stdout && stdout.trim().length > 0
        ? stdout.trim().split('\n')[0]
        : 'Walking home';
      xInput = '0';
      yInput = '0';
      setStatus(inferred, 'success');
    } catch (error) {
      console.error('API error:', error);
      setStatus('Walk home request failed', 'error');
    } finally {
      isMoving = false;
    }
  };
</script>

<div class="py-4 border-b border-neutral-600 text-xs text-neutral-200">
  <h2 class="font-semibold mb-2 text-sm text-white">Manual Controls</h2>
  <div class="flex gap-2 mb-3">
    <Button on:click={handlePenToggle} disabled={penBusy}>
      {#if penBusy}
        Toggling...
      {:else}
        Toggle Pen
      {/if}
    </Button>
    <Button on:click={() => handleMotors(true)} disabled={motorsBusy}>Enable Motors</Button>
    <Button on:click={() => handleMotors(false)} disabled={motorsBusy}>Disable Motors</Button>
    <Button on:click={handleWalkHome} disabled={isMoving}>Walk Home</Button>
  </div>
  <div class="grid grid-cols-3 gap-2">
    <label class="flex flex-col">
      X (mm)
      <input
        type="number"
        bind:value={xInput}
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        placeholder="0"
      />
    </label>
    <label class="flex flex-col">
      Y (mm)
      <input
        type="number"
        bind:value={yInput}
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        placeholder="0"
      />
    </label>
    <Button on:click={handleMove} disabled={isMoving}>
      {#if isMoving}
        Moving...
      {:else}
        Move Pen
      {/if}
    </Button>
  </div>
  {#if statusMessage}
    <p class={`mt-3 text-xs ${statusTone === 'success' ? 'text-green-400' : 'text-red-400'}`}>
      {statusMessage}
    </p>
  {/if}
</div>
