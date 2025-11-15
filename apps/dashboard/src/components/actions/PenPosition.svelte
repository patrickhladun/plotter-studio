<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { getModelNumber } from '../../lib/nextdrawCommands';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';

  export let model: string = 'Bantam Tools NextDraw™ 8511 (Default)';

  let penDownPos: string | number | null = 20;
  let penUpPos: string | number | null = 80;
  let isCycling = false;

  const handleCycle = async () => {
    const normalizedDown =
      typeof penDownPos === 'number'
        ? penDownPos.toString()
        : typeof penDownPos === 'string'
          ? penDownPos.trim()
          : '';
    const normalizedUp =
      typeof penUpPos === 'number'
        ? penUpPos.toString()
        : typeof penUpPos === 'string'
          ? penUpPos.trim()
          : '';

    if (!normalizedDown || !normalizedUp) {
      pushToast('Enter both pen down and pen up positions.', { tone: 'error' });
      return;
    }

    const downValue = Number(normalizedDown);
    const upValue = Number(normalizedUp);

    if (Number.isNaN(downValue) || Number.isNaN(upValue)) {
      pushToast('Positions must be numbers.', { tone: 'error' });
      return;
    }

    if (downValue < 0 || downValue > 100 || upValue < 0 || upValue > 100) {
      pushToast('Positions must be between 0 and 100.', { tone: 'error' });
      return;
    }

    try {
      isCycling = true;
      const modelNumber = getModelNumber(model);
      const parts = ['nextdraw'];
      if (modelNumber !== null) {
        parts.push(`-L${modelNumber}`);
      }
      parts.push('--mode', 'cycle', '--pen_pos_down', downValue.toString(), '--pen_pos_up', upValue.toString());
      const command = parts.join(' ');
      const result = await executeCommand(command, 'Cycle pen position');

      if (!result.success) {
        pushToast(result.error || 'Cycle command failed', { tone: 'error' });
        return;
      }

      pushToast(`Cycled pen: down=${downValue}, up=${upValue}`, { tone: 'success' });
    } catch (error) {
      console.error('Error:', error);
      pushToast('Cycle request failed', { tone: 'error' });
    } finally {
      isCycling = false;
    }
  };
</script>

<div class="py-4 border-b border-neutral-600 text-xs text-neutral-200">
  <h2 class="font-semibold mb-2 text-sm text-white">Pen Position</h2>
  <div class="grid grid-cols-3 gap-2">
    <label class="flex flex-col">
      Pen Down
      <input
        type="number"
        min="0"
        max="100"
        bind:value={penDownPos}
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        placeholder="20"
      />
    </label>
    <label class="flex flex-col">
      Pen Up
      <input
        type="number"
        min="0"
        max="100"
        bind:value={penUpPos}
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        placeholder="80"
      />
    </label>
    <Button on:click={handleCycle} disabled={isCycling}>
      {#if isCycling}
        Cycling...
      {:else}
        Cycle
      {/if}
    </Button>
  </div>
</div>

