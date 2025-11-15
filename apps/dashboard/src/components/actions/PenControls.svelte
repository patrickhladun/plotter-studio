<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { API_BASE_URL } from '../../lib/rpiApi';
  import { showCommandToast } from '../../lib/toastStore';
  import { buildUtilityCommand, buildManualCommand } from '../../lib/nextdrawCommands';

  export let model: string = 'Bantam Tools NextDraw™ 8511 (Default)';

  type CommandPayload = {
    ok?: boolean;
    command?: string;
    stdout?: string;
    stderr?: string;
    detail?: unknown;
    state?: string;
    segments?: CommandPayload[];
  };

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
      const command = buildUtilityCommand(model, 'toggle');
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
      const returnedCommand = payload && typeof payload.command === 'string' ? payload.command : null;
      if (returnedCommand) {
        showCommandToast('Pen toggle', returnedCommand);
      } else {
        showCommandToast('Pen toggle', command);
      }
      if (!response.ok) {
        console.error('API error:', response.statusText);
        let message = text || 'Failed to toggle pen';
        if (payload?.detail) {
          message = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
        }
        setStatus(message, 'error');
        return;
      }

      if (payload && payload.ok === false) {
        const stdout = typeof payload.stdout === 'string' ? payload.stdout.trim() : '';
        const stderr = typeof payload.stderr === 'string' ? payload.stderr.trim() : '';
        const message = stderr || stdout || 'Pen toggle failed';
        setStatus(message, 'error');
        return;
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
      const command = buildUtilityCommand(model, enable ? 'enable_xy' : 'disable_xy');
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
      const returnedCommand = payload && typeof payload.command === 'string' ? payload.command : null;
      if (returnedCommand) {
        showCommandToast(enable ? 'Enable motors' : 'Disable motors', returnedCommand);
      } else {
        showCommandToast(enable ? 'Enable motors' : 'Disable motors', command);
      }
      if (!response.ok) {
        console.error('API error:', response.statusText);
        let message = text || `Failed to ${enable ? 'enable' : 'disable'} motors`;
        if (payload?.detail) {
          message = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
        }
        setStatus(message, 'error');
        return;
      }

      if (payload && payload.ok === false) {
        const stdout = typeof payload.stdout === 'string' ? payload.stdout.trim() : '';
        const stderr = typeof payload.stderr === 'string' ? payload.stderr.trim() : '';
        const message = stderr || stdout || `Failed to ${enable ? 'enable' : 'disable'} motors`;
        setStatus(message, 'error');
        return;
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

    try {
      isMoving = true;
      const command = buildManualCommand(model, `walk ${xValue} ${yValue}`);
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
      const returnedCommand = payload && typeof payload.command === 'string' ? payload.command : null;
      if (returnedCommand) {
        showCommandToast('Move pen', returnedCommand);
      } else {
        showCommandToast('Move pen', command);
      }

      if (!response.ok) {
        console.error('API error:', response.statusText);
        const message = typeof payload?.stderr === 'string'
          ? payload.stderr
          : typeof payload?.detail === 'string'
            ? payload.detail
            : 'Move command failed';
        setStatus(message, 'error');
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
      const command = buildManualCommand(model, 'walk_home');
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
      const returnedCommand = payload && typeof payload.command === 'string' ? payload.command : null;
      if (returnedCommand) {
        showCommandToast('Walk home', returnedCommand);
      } else {
        showCommandToast('Walk home', command);
      }
      if (!response.ok) {
        console.error('API error:', response.statusText);
        let message = text || 'Walk home failed';
        if (payload?.detail) {
          message = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
        }
        setStatus(message, 'error');
        return;
      }

      if (payload && payload.ok === false) {
        const stdout = typeof payload.stdout === 'string' ? payload.stdout.trim() : '';
        const stderr = typeof payload.stderr === 'string' ? payload.stderr.trim() : '';
        const message = stderr || stdout || 'Walk home failed';
        setStatus(message, 'error');
        return;
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
