<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{ load: string }>();
  const inputId = 'svg-upload-input';

  const handleFileChange = async (event: Event) => {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }

    if (file.type !== 'image/svg+xml') {
      dispatch('load', "<p class='text-red-600'>Not an SVG file</p>");
      input.value = '';
      return;
    }

    try {
      const text = await file.text();
      dispatch('load', text);
    } catch (error) {
      console.error('Failed to read file', error);
      dispatch('load', "<p class='text-red-600'>Failed to read file</p>");
    }
  };
</script>

<div>
  <label class="block text-sm mb-1 text-white" for={inputId}>SVG file</label>
  <input
    id={inputId}
    type="file"
    accept=".svg"
    on:change={handleFileChange}
    class="block w-full text-white"
  />
</div>
