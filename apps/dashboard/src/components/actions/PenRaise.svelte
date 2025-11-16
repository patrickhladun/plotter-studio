<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';
  import { getFlag } from '../../lib/model';

  let penBusy = false;

  const handlePenRaise = async () => {
    try {
      penBusy = true;
      const parts = ['nextdraw', getFlag(), '-m', 'utility', '-M', 'raise_up'].filter(Boolean);
      const command = parts.join(' ');
      const result = await executeCommand(command, 'Pen raise');

      if (!result.success) {
        pushToast(result.error || 'Pen raise failed', { tone: 'error' });
        return;
      }

      const payload = result.payload;
      const state = payload && typeof payload.state === 'string' ? payload.state : null;
      const stdout = payload && typeof payload.stdout === 'string' ? payload.stdout : null;
      const inferredMessage = state
        ? `Pen ${state}`
        : stdout && stdout.trim().length > 0
          ? stdout.trim().split('\n')[0]
          : 'Pen raised';
      pushToast(inferredMessage, { tone: 'success' });
    } catch (error) {
      console.error('Error:', error);
      pushToast('Pen raise failed', { tone: 'error' });
    } finally {
      penBusy = false;
    }
  };
</script>

<Button on:click={handlePenRaise} disabled={penBusy}>
  {#if penBusy}
    Moving...
  {:else}
    Pen Raise
  {/if}
</Button>

