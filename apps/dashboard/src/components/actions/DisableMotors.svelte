<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { API_BASE_URL } from '../../lib/rpiApi';
  import { showCommandToast } from '../../lib/toastStore';

  const disableMotors = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/plot/disable_motors`, {
        method: 'POST',
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
