<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { filesApi, type FileMeta } from '../../lib/filesApi';
  import { pushToast } from '../../lib/toastStore';

  export let files: FileMeta[] = [];
  export let selectedFile: string = '';
  export let isLoading: boolean = false;
  let uploadInProgress: boolean = false;

  const dispatch = createEventDispatcher<{
    uploaded: string | undefined;
    fileSelected: string;
    deleted: void;
    refresh: void;
  }>();

  let dragActive = false;
  let uploadInput: HTMLInputElement | null = null;

  const formatSize = (value: number) => {
    if (value < 1024) {
      return `${value} B`;
    }
    if (value < 1024 * 1024) {
      return `${(value / 1024).toFixed(1)} KB`;
    }
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  };

  const performUpload = async (file: File | undefined | null) => {
    if (!file) {
      return;
    }

    let saved: FileMeta | null = null;
    const startTime = Date.now();
    try {
      uploadInProgress = true;
      console.log('[UploadImage] Starting upload:', file.name, file.size, 'bytes');
      saved = await filesApi.upload(file);
      const duration = Date.now() - startTime;
      console.log('[UploadImage] Upload successful:', saved?.name, `(${duration}ms)`);
      pushToast(`Uploaded ${saved?.name ?? file.name}`, { tone: 'success' });
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error('[UploadImage] Upload failed after', duration, 'ms', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const errorUrl = (error as any)?.url;
      const isTimeout = (error as any)?.isTimeout;
      
      let displayMessage = errorMessage;
      if (isTimeout) {
        displayMessage = 'Upload timeout - API server may not be running or reachable';
      } else if (errorMessage.includes('Failed to fetch')) {
        displayMessage = 'Cannot connect to API server - check if it\'s running on port 2222';
      }
      
      pushToast(`Upload failed: ${displayMessage}${errorUrl ? ` (${errorUrl})` : ''}`, { tone: 'error' });
      return;
    } finally {
      uploadInProgress = false;
    }
    
    // Dispatch event to refresh file list
    dispatch('uploaded', saved?.name);
  };

  const handleUpload = async (event: Event) => {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    await performUpload(file);
    if (input) {
      input.value = '';
    }
  };

  const handleDrop = async (event: DragEvent) => {
    event.preventDefault();
    dragActive = false;
    const file = event.dataTransfer?.files?.[0];
    await performUpload(file);
  };

  const handleDragOver = (event: DragEvent) => {
    event.preventDefault();
    dragActive = true;
  };

  const handleDragLeave = (event: DragEvent) => {
    event.preventDefault();
    dragActive = false;
  };

  const handleSelectChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? target.value : '';
    if (value) {
      dispatch('fileSelected', value);
    }
  };

  const handleDelete = async (name: string) => {
    try {
      await filesApi.remove(name);
      pushToast(`Deleted ${name}`, { tone: 'success' });
      dispatch('deleted');
    } catch (error) {
      console.error('Delete failed', error);
      pushToast('Delete failed', { tone: 'error' });
    }
  };

  const handleRefresh = () => {
    dispatch('refresh');
  };
</script>

<div class="space-y-3">
  <div
    class={`w-full border-2 border-dashed rounded px-4 py-8 text-center text-neutral-300 transition ${
      dragActive ? 'border-blue-400 bg-neutral-800/40' : 'border-neutral-600 bg-neutral-800/60'
    } ${uploadInProgress ? 'opacity-60' : ''}`}
    role="button"
    aria-label="Upload SVG by dragging or selecting a file"
    tabindex="0"
    on:dragover={handleDragOver}
    on:dragleave={handleDragLeave}
    on:drop={handleDrop}
    on:keydown={(event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        uploadInput?.click();
      }
    }}
  >
    <p class="text-sm">Drag & drop an SVG here, or</p>
    <label class="inline-flex items-center justify-center mt-2">
      <span class="bg-blue-500 hover:bg-blue-400 text-white text-xs font-medium px-3 py-1 rounded cursor-pointer">
        {uploadInProgress ? 'Uploading…' : 'Browse Files'}
      </span>
      <input
        type="file"
        accept=".svg"
        on:change={handleUpload}
        class="hidden"
        disabled={uploadInProgress}
        bind:this={uploadInput}
      />
    </label>
  </div>

  <div class="space-y-2">
    <label class="flex flex-col">
      Select file
      <select
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        value={selectedFile}
        disabled={isLoading || files.length === 0}
        on:change={handleSelectChange}
      >
        <option value="" disabled>
          {files.length === 0 ? 'No files available' : 'Choose a file'}
        </option>
        {#each files as file}
          <option value={file.name}>{file.name} ({formatSize(file.size)})</option>
        {/each}
      </select>
    </label>

    <button
      class="text-blue-300 hover:text-blue-200 self-start text-xs"
      on:click={handleRefresh}
      type="button"
      disabled={isLoading}
    >
      {isLoading ? 'Refreshing…' : 'Refresh file list'}
    </button>

    {#if selectedFile}
      <button
        class="bg-red-500 py-1 px-2 text-xs rounded cursor-pointer hover:bg-red-400 self-start"
        type="button"
        on:click={() => handleDelete(selectedFile)}
      >
        Delete selected
      </button>
    {/if}
  </div>
</div>

