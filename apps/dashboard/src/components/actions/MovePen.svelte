<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';
  import { getFlag } from '../../lib/model';

  let xInput: string | number | null = '';
  let yInput: string | number | null = '';
  let isMoving = false;

  const handleMove = async () => {
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
      pushToast('Enter at least one coordinate in millimeters.', { tone: 'error' });
      return;
    }

    const xValue = normalizedX ? Number(normalizedX) : 0;
    const yValue = normalizedY ? Number(normalizedY) : 0;

    if (Number.isNaN(xValue) || Number.isNaN(yValue)) {
      pushToast('Coordinates must be numbers.', { tone: 'error' });
      return;
    }

    try {
      isMoving = true;
      // Calculate distance from origin: sqrt(x^2 + y^2)
      const distance = Math.sqrt(xValue * xValue + yValue * yValue);
      
      const parts = ['nextdraw', getFlag(), '-m', 'utility', '-M', 'walk_mmx', '--dist', distance.toString()].filter(Boolean);
      const command = parts.join(' ');
      const result = await executeCommand(command, 'Move pen');

      if (!result.success) {
        pushToast(result.error || 'Move command failed', { tone: 'error' });
        return;
      }

      pushToast(`Walking to offset (Δx=${xValue}, Δy=${yValue})`, { tone: 'success' });
    } catch (error) {
      console.error('Error:', error);
      pushToast('Move request failed', { tone: 'error' });
    } finally {
      isMoving = false;
    }
  };
</script>

<div class="py-4 border-b border-neutral-600 text-xs text-neutral-200">
  <h2 class="font-semibold mb-2 text-sm text-white">Move Pen</h2>
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
</div>

