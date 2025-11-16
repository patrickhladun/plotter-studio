<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';
  import { getFlag } from '../../lib/model';

  let yInput: string | number | null = '';
  let isMoving = false;

  const handleWalkY = async () => {
    const normalizedY =
      typeof yInput === 'number'
        ? yInput.toString()
        : typeof yInput === 'string'
          ? yInput.trim()
          : '';

    if (!normalizedY) {
      pushToast('Enter a distance in millimeters.', { tone: 'error' });
      return;
    }

    const yValue = Number(normalizedY);

    if (Number.isNaN(yValue)) {
      pushToast('Distance must be a number.', { tone: 'error' });
      return;
    }

    try {
      isMoving = true;
      const parts = ['nextdraw', getFlag(), '-m', 'utility', '-M', 'walk_mmy', '--dist', Math.abs(yValue).toString()].filter(Boolean);
      const command = parts.join(' ');
      const result = await executeCommand(command, 'Walk Y');

      if (!result.success) {
        pushToast(result.error || 'Walk Y command failed', { tone: 'error' });
        return;
      }

      pushToast(`Walking Y: ${yValue > 0 ? '+' : ''}${yValue} mm`, { tone: 'success' });
    } catch (error) {
      console.error('Error:', error);
      pushToast('Walk Y request failed', { tone: 'error' });
    } finally {
      isMoving = false;
    }
  };
</script>

<div class="flex items-end gap-2">
  <label class="flex flex-col flex-1">
    <span class="text-xs text-neutral-400 mb-1">Y (mm)</span>
    <input
      type="number"
      bind:value={yInput}
      class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
      placeholder="0"
    />
  </label>
  <Button on:click={handleWalkY} disabled={isMoving}>
    {#if isMoving}
      Moving...
    {:else}
      Walk Y
    {/if}
  </Button>
</div>

