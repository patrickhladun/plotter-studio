<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { filesApi, type FileMeta } from '../lib/filesApi';
  import PenControls from './actions/PenControls.svelte';
  import DisableMotors from './actions/DisableMotors.svelte';
  import GetStatus from './actions/GetStatus.svelte';

  type SectionKey = 'manage' | 'edit' | 'settings' | 'plot' | 'manual';

  const dispatch = createEventDispatcher<{ preview: string }>();

  let files: FileMeta[] = [];
  let selectedFile: string = '';
  let selectedMeta: FileMeta | undefined;
  let selectedDimensions = '';
  let isLoading = false;
  let uploadInProgress = false;
  let plotting = false;
  let rotating = false;
  let renaming = false;
  let stopping = false;
  let statusMessage: string | null = null;
  let statusTone: 'success' | 'error' | null = null;
  let dragActive = false;
  let renameValue = '';
  let plotProgress: number | null = null;
  let plotRunning = false;
  let plotElapsedSeconds: number | null = null;
  let plotDistanceMm: number | null = null;
  let previewLoading = false;
  let previewError: string | null = null;
  let previewTimeSeconds: number | null = null;
  let previewDistanceMm: number | null = null;
  let uploadInput: HTMLInputElement | null = null;

  const DEFAULT_PAGE = 'a5';
  let useConstantSpeed = false;
  let speedSetting = 70;
  let brushless = false;

  let openSection: SectionKey = 'manage';

  const sections: { key: SectionKey; icon: string; label: string }[] = [
    { key: 'manage', icon: '📁', label: 'Manage Files' },
    { key: 'settings', icon: '⚙️', label: 'Print Settings' },
    { key: 'plot', icon: '🖊️', label: 'Plot Controls' },
    { key: 'manual', icon: '🤖', label: 'Manual Commands' },
  ];

  const selectSection = (key: SectionKey) => {
    openSection = key;
  };


  const setStatus = (message: string, tone: 'success' | 'error') => {
    statusMessage = message;
    statusTone = tone;
  };

  const clearStatus = () => {
    statusMessage = null;
    statusTone = null;
  };

  const clearPreview = () => {
    previewLoading = false;
    previewError = null;
    previewTimeSeconds = null;
    previewDistanceMm = null;
    if (!plotRunning) {
      plotElapsedSeconds = null;
      plotDistanceMm = null;
    }
  };

  const fetchFiles = async (preferred?: string) => {
    isLoading = true;
    try {
      const data = await filesApi.list();
      files = Array.isArray(data) ? data : [];

      if (files.length === 0) {
        selectedFile = '';
        renameValue = '';
        dispatch('preview', '');
        clearPreview();
        return;
      }

      const preferredMatch = preferred && files.find((file) => file.name === preferred);
      if (preferredMatch) {
        selectedFile = preferredMatch.name;
        renameValue = preferredMatch.name;
        await previewFile(preferredMatch.name);
        await fetchPreview(preferredMatch.name);
        return;
      }

      if (!selectedFile || !files.some((file) => file.name === selectedFile)) {
        selectedFile = files[0].name;
        renameValue = selectedFile;
        await previewFile(selectedFile);
        await fetchPreview(selectedFile);
      } else {
        renameValue = selectedFile;
        await fetchPreview(selectedFile);
      }
    } catch (error) {
      console.error('Failed to load files', error);
      const message = error instanceof Error ? error.message : 'Failed to load files';
      setStatus(message, 'error');
    } finally {
      isLoading = false;
    }
  };

  onMount(() => {
    fetchFiles();
    pollStatus();
  });

  $: selectedMeta = files.find((file) => file.name === selectedFile);
  $: selectedDimensions = describeDimensions(selectedMeta);

  const performUpload = async (file: File | undefined | null) => {
    if (!file) {
      return;
    }

    clearStatus();
    try {
      uploadInProgress = true;
      const saved = await filesApi.upload(file);
      setStatus(`Uploaded ${saved.name}`, 'success');
      await fetchFiles(saved.name);
    } catch (error) {
      console.error('Upload failed', error);
      setStatus('Upload failed. Ensure the file is an SVG.', 'error');
    } finally {
      uploadInProgress = false;
    }
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

  const handleSelectChange = async (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? target.value : '';
    if (value) {
      selectedFile = value;
      renameValue = value;
      await previewFile(value);
      await fetchPreview(value);
    }
  };

  const handlePlot = async () => {
    if (!selectedFile) {
      setStatus('Select a file before starting a plot.', 'error');
      return;
    }

    clearStatus();

    try {
      plotting = true;
      plotRunning = true;
      plotProgress = 0;
      plotElapsedSeconds = 0;
      plotDistanceMm = previewDistanceMm;
      const payload = await filesApi.plot(selectedFile, {
        page: DEFAULT_PAGE,
        s_down: 30,
        s_up: 70,
        p_down: 40,
        p_up: 70,
        handling: useConstantSpeed ? 4 : 1,
        speed: speedSetting,
        brushless,
      });

      const pid = typeof payload?.pid === 'number' ? payload.pid : undefined;
      const completed = Boolean(payload?.completed);
      const rawOutput = payload?.output;
      const outputSnippet = typeof rawOutput === 'string'
        ? (() => {
            const trimmed = rawOutput.trim();
            if (!trimmed) {
              return '';
            }
            const lines = trimmed.split('\n').map((line) => line.trim()).filter(Boolean);
            if (lines.length === 0) {
              return '';
            }
            if (lines.length >= 2 && lines[0].endsWith(':')) {
              return `${lines[0]} ${lines[1]}`;
            }
            return lines[0];
          })()
        : '';

      if (completed) {
        const summary = outputSnippet ? ` (${outputSnippet})` : '';
        setStatus(`Plot completed immediately for ${selectedFile}${summary}`, 'success');
        plotRunning = false;
        plotProgress = 100;
        plotElapsedSeconds = 0;
        pollStatus();
        return;
      }

      const pidLabel = pid ? ` (pid ${pid})` : '';
      setStatus(`Plot started for ${selectedFile}${pidLabel}`, 'success');
      pollStatus();
    } catch (error) {
      console.error('Plot failed', error);
      const message = error instanceof Error ? error.message : 'Plot start failed';
      setStatus(message, 'error');
      plotRunning = false;
      plotProgress = null;
      plotElapsedSeconds = null;
    } finally {
      plotting = false;
    }
  };

  const handleRotate = async (angle: number) => {
    if (!selectedFile) {
      setStatus('Select a file before rotating.', 'error');
      return;
    }

    clearStatus();

    try {
      rotating = true;
      await filesApi.rotate(selectedFile, angle);
      await fetchFiles(selectedFile);
      setStatus(`Rotated ${selectedFile}`, 'success');
      await fetchPreview(selectedFile);
    } catch (error) {
      console.error('Rotation failed', error);
      const message = error instanceof Error ? error.message : 'Rotation failed';
      setStatus(message, 'error');
    } finally {
      rotating = false;
    }
  };

  const handleRename = async () => {
    if (!selectedFile) {
      setStatus('Select a file before renaming.', 'error');
      return;
    }

    const trimmed = renameValue.trim();
    if (!trimmed) {
      setStatus('Filename cannot be empty.', 'error');
      return;
    }

    clearStatus();

    try {
      renaming = true;
      const updated = await filesApi.rename(selectedFile, trimmed);
      selectedFile = updated.name;
      renameValue = updated.name;
      await fetchFiles(updated.name);
      await fetchPreview(updated.name);
      setStatus(`Renamed to ${updated.name}`, 'success');
    } catch (error) {
      console.error('Rename failed', error);
      const message = error instanceof Error ? error.message : 'Rename failed';
      setStatus(message, 'error');
    } finally {
      renaming = false;
    }
  };

  const handleStopPlot = async () => {
    clearStatus();
    try {
      stopping = true;
      await filesApi.cancelPlot();
      setStatus('Plot canceled.', 'success');
      plotRunning = false;
      plotProgress = null;
      pollStatus();
    } catch (error) {
      console.error('Stop failed', error);
      const message = error instanceof Error ? error.message : 'Failed to stop plot';
      setStatus(message, 'error');
    } finally {
      stopping = false;
    }
  };

  const pollStatus = async () => {
    try {
      const data = await filesApi.status();
      plotRunning = Boolean(data?.running);
      const rawProgress = data?.progress;
      plotProgress = typeof rawProgress === 'number' ? rawProgress : null;
      const rawElapsed = data?.elapsed_seconds;
      plotElapsedSeconds = typeof rawElapsed === 'number' ? rawElapsed : null;
      const rawDistance = data?.distance_mm;
      plotDistanceMm = typeof rawDistance === 'number' ? rawDistance : plotDistanceMm;
      if (!plotRunning && plotDistanceMm == null && previewDistanceMm != null) {
        plotDistanceMm = previewDistanceMm;
      }
      const errorMessage = typeof data?.error === 'string' ? data.error : null;
      if (errorMessage && statusMessage !== errorMessage) {
        setStatus(errorMessage, 'error');
        plotRunning = false;
        plotProgress = null;
        plotElapsedSeconds = null;
      }
    } catch (error) {
      // ignore status polling errors
    }
  };

  const formatDuration = (value: number) => {
    if (!Number.isFinite(value) || value < 0) {
      return '—';
    }
    const totalSeconds = Math.round(value);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    }
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    }
    return `${seconds}s`;
  };

  const formatDistance = (mm: number) => {
    if (!Number.isFinite(mm) || mm < 0) {
      return '—';
    }
    if (mm >= 1000) {
      return `${(mm / 1000).toFixed(2)} m`;
    }
    if (mm >= 10) {
      return `${(mm / 10).toFixed(1)} cm`;
    }
    return `${mm.toFixed(1)} mm`;
  };

  const fetchPreview = async (name: string | undefined) => {
    if (!name) {
      clearPreview();
      return;
    }

    previewLoading = true;
    previewError = null;
    try {
      const data = await filesApi.preview(name, {
        handling: useConstantSpeed ? 4 : 1,
        speed: speedSetting,
        brushless,
      });
      const timeValue = data?.estimated_seconds;
      const distanceValue = data?.distance_mm;
      previewTimeSeconds = typeof timeValue === 'number' ? timeValue : null;
      previewDistanceMm = typeof distanceValue === 'number' ? distanceValue : null;
      if (!plotRunning) {
        plotElapsedSeconds = previewTimeSeconds;
        plotDistanceMm = previewDistanceMm;
      }
    } catch (error) {
      console.error('Preview failed', error);
      previewError = 'Unable to estimate plot time.';
      previewTimeSeconds = null;
      previewDistanceMm = null;
    } finally {
      previewLoading = false;
    }
  };

  const previewFile = async (name: string) => {
    try {
      const svg = await filesApi.raw(name);
      dispatch('preview', svg);
    } catch (error) {
      console.error('Preview failed', error);
      setStatus('Preview failed', 'error');
    }
  };

  const handleDelete = async (name: string) => {
    clearStatus();
    try {
      await filesApi.remove(name);
      setStatus(`Deleted ${name}`, 'success');
      await fetchFiles();
    } catch (error) {
      console.error('Delete failed', error);
      setStatus('Delete failed', 'error');
    }
  };

  const formatSize = (value: number) => {
    if (value < 1024) {
      return `${value} B`;
    }
    if (value < 1024 * 1024) {
      return `${(value / 1024).toFixed(1)} KB`;
    }
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  };

  type LengthInfo = { mm: number; approx: boolean } | null;

  const lengthToMm = (value?: string | null): LengthInfo => {
    if (!value) {
      return null;
    }

    const match = value.trim().match(/^([+-]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)$/);
    if (!match) {
      return null;
    }

    const numeric = Number(match[1]);
    if (!Number.isFinite(numeric)) {
      return null;
    }

    const unit = match[2].toLowerCase();
    const mmPerUnit: Record<string, { factor: number; approx?: boolean }> = {
      mm: { factor: 1 },
      millimeter: { factor: 1 },
      millimeters: { factor: 1 },
      cm: { factor: 10 },
      centimeter: { factor: 10 },
      centimeters: { factor: 10 },
      m: { factor: 1000 },
      meter: { factor: 1000 },
      meters: { factor: 1000 },
      in: { factor: 25.4 },
      inch: { factor: 25.4 },
      inches: { factor: 25.4 },
      pt: { factor: 25.4 / 72, approx: true },
      pc: { factor: 25.4 / 6, approx: true },
      px: { factor: 25.4 / 96, approx: true },
      q: { factor: 0.25 },
    };

    if (!unit) {
      return null;
    }

    const mapping = mmPerUnit[unit];
    if (!mapping) {
      return null;
    }

    return { mm: numeric * mapping.factor, approx: Boolean(mapping.approx) };
  };

  const formatMm = (value: number) => {
    if (!Number.isFinite(value)) {
      return '';
    }
    if (Math.abs(value) >= 1) {
      return value.toFixed(2).replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1');
    }
    return value.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
  };

  const describeDimensions = (file: FileMeta | undefined) => {
    if (!file) {
      return '';
    }

    const { width, height, viewBox } = file;
    const widthMm = lengthToMm(width || undefined);
    const heightMm = lengthToMm(height || undefined);

    if (widthMm && heightMm) {
      const approx = widthMm.approx || heightMm.approx;
      const prefix = approx ? '≈ ' : '';
      return `${prefix}${formatMm(widthMm.mm)} × ${formatMm(heightMm.mm)} mm`;
    }

    if (viewBox) {
      const parts = viewBox.split(/\s+/);
      if (parts.length === 4) {
        const widthVal = Number(parts[2]);
        const heightVal = Number(parts[3]);
        if (!Number.isNaN(widthVal) && !Number.isNaN(heightVal)) {
          return `${widthVal} × ${heightVal} (viewBox)`;
        }
      }
    }

    if (width && height) {
      return `${width} × ${height}`;
    }

    return viewBox ? `viewBox: ${viewBox}` : '';
  };
</script>

<div class="text-xs text-neutral-200">
  <div class="mb-3 text-center text-sm font-semibold uppercase tracking-wide text-neutral-100">
    Plotter Studio
  </div>
  {#if statusMessage}
    <p class={`mb-3 text-xs ${statusTone === 'success' ? 'text-green-400' : 'text-red-400'}`}>
      {statusMessage}
    </p>
  {/if}

  <div class="flex h-full">
    <nav class="flex w-12 flex-col items-center gap-2 py-2 bg-neutral-900/40">
      {#each sections as section}
        <button
          class={`flex h-10 w-10 items-center justify-center rounded ${
            openSection === section.key ? 'bg-neutral-600 text-white' : 'text-neutral-300 hover:bg-neutral-700'
          }`}
          type="button"
          aria-label={section.label}
          aria-pressed={openSection === section.key}
          on:click={() => selectSection(section.key)}
        >
          <span class="text-lg leading-none">{section.icon}</span>
        </button>
      {/each}
    </nav>

    <div class="flex-1 min-w-0 space-y-4 px-4 py-3">
      {#if openSection === 'manage'}
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
                bind:value={selectedFile}
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
              on:click={() => fetchFiles()}
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

        
      {:else if openSection === 'settings'}
        {#if selectedFile}
          <div class="space-y-3">
            <label class="flex items-center gap-2">
              <input
                type="checkbox"
                bind:checked={useConstantSpeed}
                on:change={() => fetchPreview(selectedFile)}
              />
              <span>Use constant speed</span>
            </label>

            {#if useConstantSpeed}
              <label class="flex flex-col gap-1">
                <span>Speed: {speedSetting}%</span>
                <input
                  type="range"
                  min="1"
                  max="100"
                  bind:value={speedSetting}
                  on:change={() => fetchPreview(selectedFile)}
                />
              </label>
            {/if}

            <label class="flex items-center gap-2">
              <input
                type="checkbox"
                bind:checked={brushless}
                on:change={() => fetchPreview(selectedFile)}
              />
              <span>Brushless head</span>
            </label>

            {#if previewLoading}
              <p class="text-neutral-400 text-xs">Estimating plot time…</p>
            {:else if previewError}
              <p class="text-red-400 text-xs">{previewError}</p>
            {:else if previewTimeSeconds !== null || previewDistanceMm !== null}
              <div class="space-y-1 text-xs text-neutral-300">
                {#if previewTimeSeconds !== null}
                  <p>Estimated time: {formatDuration(previewTimeSeconds)}</p>
                {/if}
                {#if previewDistanceMm !== null}
                  <p>Estimated distance: {formatDistance(previewDistanceMm)}</p>
                {/if}
              </div>
            {/if}
          </div>
        {:else}
          <p class="text-neutral-400 text-xs">Select a file to configure print settings.</p>
        {/if}
      {:else if openSection === 'plot'}
        {#if selectedFile}
          {#if plotProgress !== null}
            <div class="flex w-full items-center gap-2">
              <div class="h-2 flex-1 rounded bg-neutral-700">
                <div
                  class="h-full rounded bg-green-400 transition-all"
                  style={`width:${Math.max(0, Math.min(plotProgress, 100))}%`}
                ></div>
              </div>
              <span class="text-xs text-neutral-300">{Math.round(plotProgress)}%</span>
            </div>
          {/if}

          <div class="space-y-1 text-xs text-neutral-300">
            <p>Plot time: {plotElapsedSeconds !== null ? formatDuration(plotElapsedSeconds) : previewTimeSeconds !== null ? formatDuration(previewTimeSeconds) : '—'}</p>
            <p>Distance: {plotDistanceMm !== null ? formatDistance(plotDistanceMm) : previewDistanceMm !== null ? formatDistance(previewDistanceMm) : '—'}</p>
          </div>

          <div class="flex flex-wrap gap-2">
            <button
              class="bg-green-500 py-1 px-2 text-xs rounded cursor-pointer hover:bg-green-400"
              type="button"
              on:click={handlePlot}
              disabled={plotting || rotating || plotRunning}
            >
              {plotting ? 'Starting…' : 'Start Plot'}
            </button>
            <button
              class="text-blue-300 hover:text-blue-200 text-xs"
              type="button"
              on:click={pollStatus}
            >
              Refresh status
            </button>
            {#if plotRunning}
              <button
                class="bg-yellow-500 py-1 px-2 text-xs rounded cursor-pointer hover:bg-yellow-400"
                type="button"
                on:click={handleStopPlot}
                disabled={stopping}
              >
                {stopping ? 'Stopping…' : 'Stop Plot'}
              </button>
            {/if}
          </div>
        {:else}
          <p class="text-neutral-400 text-xs">Select a file to view plotting controls.</p>
        {/if}
      {:else}
        <div class="space-y-3">
          <PenControls />
          <DisableMotors />
          <GetStatus />
        </div>
      {/if}
    </div>
  </div>
</div>
