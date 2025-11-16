<script lang="ts">
  import { filesApi } from '../../lib/filesApi';
  import { pushToast } from '../../lib/toastStore';
  import { createEventDispatcher } from 'svelte';

  export let selectedFile: string = '';
  export let selectedDimensions: string = '';
  export let renameValue: string = '';
  export let renaming: boolean = false;
  export let rotating: boolean = false;

  const dispatch = createEventDispatcher<{
    renamed: string;
    rotated: void;
  }>();

  const handleRename = async () => {
    if (!selectedFile) {
      pushToast('Select a file before renaming.', { tone: 'error' });
      return;
    }

    const trimmed = renameValue.trim();
    if (!trimmed) {
      pushToast('Filename cannot be empty.', { tone: 'error' });
      return;
    }

    try {
      renaming = true;
      const updated = await filesApi.rename(selectedFile, trimmed);
      pushToast(`Renamed to ${updated.name}`, { tone: 'success' });
      dispatch('renamed', updated.name);
    } catch (error) {
      console.error('Rename failed', error);
      const message = error instanceof Error ? error.message : 'Rename failed';
      pushToast(message, { tone: 'error' });
    } finally {
      renaming = false;
    }
  };

  const handleRotate = async (angle: number) => {
    if (!selectedFile) {
      pushToast('Select a file before rotating.', { tone: 'error' });
      return;
    }

    try {
      rotating = true;
      await filesApi.rotate(selectedFile, angle);
      pushToast(`Rotated ${selectedFile}`, { tone: 'success' });
      dispatch('rotated');
    } catch (error) {
      console.error('Rotation failed', error);
      const message = error instanceof Error ? error.message : 'Rotation failed';
      pushToast(message, { tone: 'error' });
    } finally {
      rotating = false;
    }
  };
</script>

{#if selectedFile}
  <div class="space-y-3">
    {#if selectedDimensions}
      <p class="text-neutral-400 text-xs">Dimensions: {selectedDimensions}</p>
    {/if}

    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-2">
      <input
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100 flex-1"
        type="text"
        bind:value={renameValue}
        placeholder="Filename"
        disabled={renaming}
      />
      <button
        class="bg-neutral-500 hover:bg-neutral-400 text-white text-xs font-medium px-3 py-1 rounded self-start sm:self-auto"
        type="button"
        on:click={handleRename}
        disabled={renaming}
      >
        {renaming ? 'Renaming…' : 'Save name'}
      </button>
    </div>

    <div class="flex gap-2">
      <button
        class="bg-neutral-600 py-1 px-2 text-xs rounded cursor-pointer hover:bg-neutral-500 self-start"
        type="button"
        on:click={() => handleRotate(-90)}
        disabled={rotating}
      >
        {rotating ? 'Rotating…' : 'Rotate -90°'}
      </button>
      <button
        class="bg-neutral-600 py-1 px-2 text-xs rounded cursor-pointer hover:bg-neutral-500 self-start"
        type="button"
        on:click={() => handleRotate(90)}
        disabled={rotating}
      >
        {rotating ? 'Rotating…' : 'Rotate +90°'}
      </button>
    </div>
  </div>
{:else}
  <p class="text-neutral-400 text-xs">Select a file to edit its details.</p>
{/if}

