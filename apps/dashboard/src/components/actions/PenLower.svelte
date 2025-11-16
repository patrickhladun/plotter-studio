<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';
  import { getFlag } from '../../lib/model';

  let penBusy = false;

  const handlePenLower = async () => {
    try {
      penBusy = true;
      const parts = ['nextdraw', getFlag(), '-m', 'utility', '-M', 'lower_up'].filter(Boolean);
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

