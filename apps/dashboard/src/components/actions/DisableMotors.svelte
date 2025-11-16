<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { buildUtilityCommand } from '../../lib/nextdrawCommands';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';
  import { model } from '../../lib/model';

  let motorsBusy = false;

  const disableMotors = async () => {
    try {
      motorsBusy = true;
      const command = buildUtilityCommand($model, 'disable_xy');
      const result = await executeCommand(command, 'Disable motors');

      if (!result.success) {
        pushToast(result.error || 'Failed to disable motors', { tone: 'error' });
        return;
      }

      const payload = result.payload;
      const stdout = payload && typeof payload.stdout === 'string' ? payload.stdout : null;
      const inferred = stdout && stdout.trim().length > 0
        ? stdout.trim().split('\n')[0]
        : 'Motors disabled';
      pushToast(inferred, { tone: 'success' });
    } catch (error) {
      console.error('Error:', error);
      pushToast('Motor disable failed', { tone: 'error' });
    } finally {
      motorsBusy = false;
    }
  };
</script>

<Button on:click={disableMotors} disabled={motorsBusy}>
  {#if motorsBusy}
    Disabling...
  {:else}
    Disable Motors
  {/if}
</Button>
