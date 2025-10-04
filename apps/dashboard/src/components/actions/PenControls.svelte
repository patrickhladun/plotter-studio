<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { API_BASE_URL } from '../../lib/rpiApi';

  let xInput: string | number | null = '';
  let yInput: string | number | null = '';
  let isMoving = false;
  let statusMessage: string | null = null;
  let statusTone: 'success' | 'error' | null = null;

  const setStatus = (message: string, tone: 'success' | 'error') => {
    statusMessage = message;
    statusTone = tone;
  };

  const clearStatus = () => {
    statusMessage = null;
    statusTone = null;
  };

  const handlePenUp = async () => {
    clearStatus();
    try {
      const response = await fetch(`${API_BASE_URL}/pen/up`, { method: 'POST' });
      if (!response.ok) {
        console.error('API error:', response.statusText);
        setStatus('Failed to raise pen', 'error');
        return;
      }
      setStatus('Pen raised', 'success');
    } catch (error) {
      console.error('API error:', error);
      setStatus('Pen up request failed', 'error');
    }
  };

  const handlePenDown = async () => {
    clearStatus();
    try {
      const response = await fetch(`${API_BASE_URL}/pen/down`, { method: 'POST' });
      if (!response.ok) {
        console.error('API error:', response.statusText);
        setStatus('Failed to lower pen', 'error');
        return;
      }
      setStatus('Pen lowered', 'success');
    } catch (error) {
      console.error('API error:', error);
      setStatus('Pen down request failed', 'error');
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
      const response = await fetch(`${API_BASE_URL}/move`, {
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

      setStatus(`Move command sent (x=${xValue}, y=${yValue})`, 'success');
    } catch (error) {
      console.error('API error:', error);
      setStatus('Move request failed', 'error');
    } finally {
      isMoving = false;
    }
  };

  const handleHome = async () => {
    clearStatus();
    try {
      isMoving = true;
      const response = await fetch(`${API_BASE_URL}/home`, { method: 'POST' });
      if (!response.ok) {
        console.error('API error:', response.statusText);
        setStatus('Home command failed', 'error');
        return;
      }
      xInput = '0';
      yInput = '0';
      setStatus('Returning to origin (0, 0)', 'success');
    } catch (error) {
      console.error('API error:', error);
      setStatus('Home request failed', 'error');
    } finally {
      isMoving = false;
    }
  };
</script>

<div class="py-4 border-b border-neutral-600 text-xs text-neutral-200">
  <h2 class="font-semibold mb-2 text-sm text-white">Manual Controls</h2>
  <div class="flex gap-2 mb-3">
    <Button on:click={handlePenUp}>Pen Up</Button>
    <Button on:click={handlePenDown}>Pen Down</Button>
    <Button on:click={handleHome} disabled={isMoving}>Home</Button>
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
