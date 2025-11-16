<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';
  import { getFlag } from '../../lib/model';

  let xInput: string | number | null = '';
  let isMoving = false;

  const handleWalkX = async () => {
    const normalizedX =
      typeof xInput === 'number'
        ? xInput.toString()
        : typeof xInput === 'string'
          ? xInput.trim()
          : '';

    if (!normalizedX) {
      pushToast('Enter a distance in millimeters.', { tone: 'error' });
      return;
    }

    const xValue = Number(normalizedX);

    if (Number.isNaN(xValue)) {
      pushToast('Distance must be a number.', { tone: 'error' });
      return;
    }

    try {
      isMoving = true;
      const parts = ['nextdraw', getFlag(), '-m', 'utility', '-M', 'walk_mmx', '--dist', Math.abs(xValue).toString()].filter(Boolean);
      const command = parts.join(' ');
      const result = await executeCommand(command, 'Walk X');

      if (!result.success) {
        pushToast(result.error || 'Walk X command failed', { tone: 'error' });
        return;
      }

      pushToast(`Walking X: ${xValue > 0 ? '+' : ''}${xValue} mm`, { tone: 'success' });
    } catch (error) {
      console.error('Error:', error);
      pushToast('Walk X request failed', { tone: 'error' });
    } finally {
      isMoving = false;
    }
  };
</script>

<div class="flex items-end gap-2">
  <label class="flex flex-col flex-1">
    <span class="text-xs text-neutral-400 mb-1">X (mm)</span>
    <input
      type="number"
      bind:value={xInput}
      class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
      placeholder="0"
    />
  </label>
  <Button on:click={handleWalkX} disabled={isMoving}>
    {#if isMoving}
      Moving...
    {:else}
      Walk X
    {/if}
  </Button>
</div>

