<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { API_BASE_URL } from '../../lib/rpiApi';

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/status`);
      if (!response.ok) {
        console.error('API error:', response.statusText);
        return;
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        console.log(data);
      } else {
        console.log(await response.text());
      }
    } catch (error) {
      console.error('API error:', error);
    }
  };
</script>

<Button on:click={fetchStatus}>Get Status</Button>
