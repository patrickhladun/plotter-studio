<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { buildUtilityCommand } from '../../lib/nextdrawCommands';
  import { executeCommand } from '../../lib/commandExecutor';

  export let model: string = 'Bantam Tools NextDraw™ 8511 (Default)';

  const disableMotors = async () => {
    try {
      const command = buildUtilityCommand(model, 'disable_xy');
      await executeCommand(command, 'Disable motors');
    } catch (error) {
      console.error('Error:', error);
    }
  };
</script>

<Button on:click={disableMotors}>Disable Motors</Button>
