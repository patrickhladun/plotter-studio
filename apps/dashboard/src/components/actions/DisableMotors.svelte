<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { API_BASE_URL } from '../../lib/rpiApi';

  const disableMotors = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/disable_motors`, {
        method: 'POST',
      });

      if (!response.ok) {
        console.error('API error:', response.statusText);
        return;
      }

      const payload = await response.text();
      console.log(payload);
    } catch (error) {
      console.error('API error:', error);
    }
  };
</script>

<Button on:click={disableMotors}>Disable Motors</Button>
