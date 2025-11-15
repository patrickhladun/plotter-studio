<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { buildUtilityCommandWithoutModel } from '../../lib/nextdrawCommands';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';

  let isMoving = false;

  const handleWalkHome = async () => {
    try {
      isMoving = true;
      const command = buildUtilityCommandWithoutModel('walk_home');
      const result = await executeCommand(command, 'Walk home');

      if (!result.success) {
        pushToast(result.error || 'Walk home failed', { tone: 'error' });
        return;
      }

      const payload = result.payload;
      const stdout = payload && typeof payload.stdout === 'string' ? payload.stdout : null;
      const inferred = stdout && stdout.trim().length > 0
        ? stdout.trim().split('\n')[0]
        : 'Walking home';
      pushToast(inferred, { tone: 'success' });
    } catch (error) {
      console.error('Error:', error);
      pushToast('Walk home request failed', { tone: 'error' });
    } finally {
      isMoving = false;
    }
  };
</script>

<Button on:click={handleWalkHome} disabled={isMoving}>
  {#if isMoving}
    Walking...
  {:else}
    Walk Home
  {/if}
</Button>

