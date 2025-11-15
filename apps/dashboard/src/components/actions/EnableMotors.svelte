<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { buildUtilityCommand } from '../../lib/nextdrawCommands';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';

  export let model: string = 'Bantam Tools NextDraw™ 8511 (Default)';

  let motorsBusy = false;

  const enableMotors = async () => {
    try {
      motorsBusy = true;
      const command = buildUtilityCommand(model, 'enable_xy');
      const result = await executeCommand(command, 'Enable motors');

      if (!result.success) {
        pushToast(result.error || 'Failed to enable motors', { tone: 'error' });
        return;
      }

      const payload = result.payload;
      const stdout = payload && typeof payload.stdout === 'string' ? payload.stdout : null;
      const inferred = stdout && stdout.trim().length > 0
        ? stdout.trim().split('\n')[0]
        : 'Motors enabled';
      pushToast(inferred, { tone: 'success' });
    } catch (error) {
      console.error('Error:', error);
      pushToast('Motor enable failed', { tone: 'error' });
    } finally {
      motorsBusy = false;
    }
  };
</script>

<Button on:click={enableMotors} disabled={motorsBusy}>
  {#if motorsBusy}
    Enabling...
  {:else}
    Enable Motors
  {/if}
</Button>

