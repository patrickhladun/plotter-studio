<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { getModelNumber } from '../../lib/nextdrawCommands';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';

  export let model: string = 'Bantam Tools NextDraw™ 8511 (Default)';

  let penBusy = false;

  const handlePenLower = async () => {
    try {
      penBusy = true;
      const modelNumber = getModelNumber(model);
      const parts = ['nextdraw'];
      if (modelNumber !== null) {
        parts.push(`-L${modelNumber}`);
      }
      parts.push('-m', 'utility', '-M', 'lower_up');
      const command = parts.join(' ');
      const result = await executeCommand(command, 'Pen lower');

      if (!result.success) {
        pushToast(result.error || 'Pen lower failed', { tone: 'error' });
        return;
      }

      const payload = result.payload;
      const state = payload && typeof payload.state === 'string' ? payload.state : null;
      const stdout = payload && typeof payload.stdout === 'string' ? payload.stdout : null;
      const inferredMessage = state
        ? `Pen ${state}`
        : stdout && stdout.trim().length > 0
          ? stdout.trim().split('\n')[0]
          : 'Pen lowered';
      pushToast(inferredMessage, { tone: 'success' });
    } catch (error) {
      console.error('Error:', error);
      pushToast('Pen lower failed', { tone: 'error' });
    } finally {
      penBusy = false;
    }
  };
</script>

<Button on:click={handlePenLower} disabled={penBusy}>
  {#if penBusy}
    Moving...
  {:else}
    Pen Lower
  {/if}
</Button>

