<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { API_BASE_URL } from '../../lib/rpiApi';
  import { showCommandToast } from '../../lib/toastStore';
  import { buildUtilityCommand } from '../../lib/nextdrawCommands';

  export let model: string = 'Bantam Tools NextDraw™ 8511 (Default)';

  const disableMotors = async () => {
    try {
      const command = buildUtilityCommand(model, 'disable_xy');
      const formData = new FormData();
      formData.append('command', command);
      const response = await fetch(`${API_BASE_URL}/plot`, {
        method: 'POST',
        body: formData,
      });

      const body = await response.text();
      let payload: { command?: string } | null = null;
      try {
        payload = body ? JSON.parse(body) : null;
      } catch {
        payload = null;
      }

      if (payload?.command) {
        showCommandToast('Disable motors', payload.command);
      }

      if (!response.ok) {
        console.error('API error:', response.statusText);
      }
    } catch (error) {
      console.error('API error:', error);
    }
  };
</script>

<Button on:click={disableMotors}>Disable Motors</Button>
