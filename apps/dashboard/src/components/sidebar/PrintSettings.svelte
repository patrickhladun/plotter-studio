<script lang="ts">
  import type { PlotSettings } from '../../lib/filesApi';
  import { createEventDispatcher } from 'svelte';
  import Button from '../Button/Button.svelte';
  import { getModelNumber } from '../../lib/nextdrawCommands';
  import { executeCommand } from '../../lib/commandExecutor';
  import { pushToast } from '../../lib/toastStore';
  import { filesApi } from '../../lib/filesApi';

  export let selectedFile: string = '';
  export let selectedProfile: string = '';
  export let availablePlotProfiles: { name: string; settings: PlotSettings; protected?: boolean }[] = [];
  export let newProfileName: string = '';
  export let handlingMode: number = 1;
  export let speedSetting: number = 70;
  export let speedPenDown: number;
  export let speedPenUp: number;
  export let penPosDown: number;
  export let penPosUp: number;
  export let devicePenliftMode: number = 1;
  export let model: string = 'Bantam Tools NextDraw™ 8511 (Default)';
  export let selectedLayer: string | null = null;
  export let previewLoading: boolean = false;
  export let previewError: string | null = null;
  export let previewTimeSeconds: number | null = null;
  export let previewDistanceMm: number | null = null;

  let isCycling = false;
  let availableLayers: string[] = [];
  let layersLoading = false;

  const dispatch = createEventDispatcher<{
    profileChange: string;
    profileSave: void;
    profileDelete: void;
    handlingChange: number;
    speedChange: number;
    penliftChange: number;
    layerChange: string | null;
    settingsChange: void;
  }>();

  let lastFetchedFile: string | null = null;

  $: if (selectedFile && selectedFile !== lastFetchedFile) {
    lastFetchedFile = selectedFile;
    fetchLayers();
  } else if (!selectedFile) {
    availableLayers = [];
    selectedLayer = null;
    lastFetchedFile = null;
  }

  async function fetchLayers() {
    if (!selectedFile) {
      availableLayers = [];
      return;
    }
    try {
      layersLoading = true;
      const result = await filesApi.getLayers(selectedFile);
      availableLayers = result?.layers || [];
      // If current selection is not in available layers, reset to null
      if (selectedLayer && !availableLayers.includes(selectedLayer)) {
        selectedLayer = null;
        dispatch('layerChange', null);
      }
    } catch (error) {
      console.error('Failed to fetch layers:', error);
      availableLayers = [];
    } finally {
      layersLoading = false;
    }
  }

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

  const handleProfileChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? target.value : selectedProfile;
    dispatch('profileChange', value);
  };

  const handleSaveProfile = () => {
    dispatch('profileSave');
  };

  const handleDeleteProfile = () => {
    dispatch('profileDelete');
  };

  const handleHandlingChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? Number(target.value) : handlingMode;
    dispatch('handlingChange', value);
  };

  const handleSpeedChange = () => {
    dispatch('speedChange', speedSetting);
  };

  const handlePenliftChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? Number(target.value) : devicePenliftMode;
    dispatch('penliftChange', value);
  };

  const handleSettingsChange = () => {
    dispatch('settingsChange');
  };

  const handleLayerChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target?.value || null;
    selectedLayer = value === '' ? null : value;
    dispatch('layerChange', selectedLayer);
    dispatch('settingsChange');
  };

  const handleCycle = async () => {
    if (penPosDown === null || penPosDown === undefined || penPosUp === null || penPosUp === undefined) {
      pushToast('Enter both pen down and pen up positions.', { tone: 'error' });
      return;
    }

    const downValue = Number(penPosDown);
    const upValue = Number(penPosUp);

    if (Number.isNaN(downValue) || Number.isNaN(upValue)) {
      pushToast('Positions must be numbers.', { tone: 'error' });
      return;
    }

    if (downValue < 0 || downValue > 100 || upValue < 0 || upValue > 100) {
      pushToast('Positions must be between 0 and 100.', { tone: 'error' });
      return;
    }

    try {
      isCycling = true;
      const modelNumber = getModelNumber(model);
      const parts = ['nextdraw'];
      if (modelNumber !== null) {
        parts.push(`-L${modelNumber}`);
      }
      parts.push('--mode', 'cycle', '--pen_pos_down', downValue.toString(), '--pen_pos_up', upValue.toString());
      const command = parts.join(' ');
      const result = await executeCommand(command, 'Cycle pen position');

      if (!result.success) {
        pushToast(result.error || 'Cycle command failed', { tone: 'error' });
        return;
      }

      pushToast(`Cycled pen: down=${downValue}, up=${upValue}`, { tone: 'success' });
    } catch (error) {
      console.error('Error:', error);
      pushToast('Cycle request failed', { tone: 'error' });
    } finally {
      isCycling = false;
    }
  };
</script>

{#if selectedFile}
  <div class="mt-4 border-t border-neutral-700 pt-4 space-y-3">
    <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-400">
      Print Settings
    </h3>
    <div class="space-y-1">
      <label class="flex flex-col text-xs text-neutral-300 gap-1">
        Preset
        <select
          class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
          value={selectedProfile}
          on:change={handleProfileChange}
        >
          {#each availablePlotProfiles as profile}
            <option value={profile.name}>{profile.name}</option>
          {/each}
        </select>
      </label>
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <input
          type="text"
          class="flex-1 rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
          placeholder="Preset name"
          bind:value={newProfileName}
        />
        <button
          class="bg-blue-500 hover:bg-blue-400 text-white text-xs font-medium px-3 py-1 rounded"
          type="button"
          on:click={handleSaveProfile}
        >
          Save preset
        </button>
        {#if availablePlotProfiles.find((profile) => profile.name === selectedProfile)?.protected !== true}
          <button
            class="bg-red-500 hover:bg-red-400 text-white text-xs font-medium px-3 py-1 rounded"
            type="button"
            on:click={handleDeleteProfile}
          >
            Delete preset
          </button>
        {/if}
      </div>
    </div>

    <label class="flex flex-col gap-1 text-xs text-neutral-300">
      <span>Handling mode</span>
      <select
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        value={handlingMode}
        on:change={handleHandlingChange}
      >
        <option value={1}>1 — Technical drawing (default)</option>
        <option value={2}>2 — Handwriting</option>
        <option value={3}>3 — Sketching</option>
        <option value={4}>4 — Constant speed</option>
        <option value={5}>5 — Off (no handling flag)</option>
      </select>
    </label>

    {#if handlingMode === 4}
      <label class="flex flex-col gap-1">
        <span>Speed: {speedSetting}%</span>
        <input
          type="range"
          min="1"
          max="100"
          bind:value={speedSetting}
          on:change={handleSpeedChange}
        />
      </label>
    {/if}

    <label class="flex flex-col gap-1 text-xs text-neutral-300">
      <span>Pen lift mode</span>
      <select
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        value={devicePenliftMode}
        on:change={handlePenliftChange}
      >
        <option value={1}>1 — Default (AxiDraw)</option>
        <option value={2}>2 — NextDraw Future</option>
        <option value={3}>3 — Brushless upgrade</option>
      </select>
    </label>

    {#if availableLayers.length > 0}
      <label class="flex flex-col gap-1 text-xs text-neutral-300">
        <span>Layer</span>
        <select
          class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
          value={selectedLayer || ''}
          on:change={handleLayerChange}
          disabled={layersLoading}
        >
          <option value="">All layers (default)</option>
          {#each availableLayers as layer}
            <option value={layer}>{layer}</option>
          {/each}
        </select>
      </label>
    {/if}

    <div class="grid gap-2 sm:grid-cols-2">
      <label class="flex flex-col text-xs gap-1">
        <span>Pen-down speed (%)</span>
        <input
          type="number"
          min="1"
          max="100"
          step="1"
          class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
          bind:value={speedPenDown}
          on:change={handleSettingsChange}
        />
      </label>
      <label class="flex flex-col text-xs gap-1">
        <span>Pen-up speed (%)</span>
        <input
          type="number"
          min="1"
          max="100"
          step="1"
          class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
          bind:value={speedPenUp}
          on:change={handleSettingsChange}
        />
      </label>
      <label class="flex flex-col text-xs gap-1">
        <span>Pen-down position</span>
        <input
          type="number"
          min="0"
          max="100"
          step="1"
          class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
          bind:value={penPosDown}
          on:change={handleSettingsChange}
        />
      </label>
      <label class="flex flex-col text-xs gap-1">
        <span>Pen-up position</span>
        <input
          type="number"
          min="0"
          max="100"
          step="1"
          class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
          bind:value={penPosUp}
          on:change={handleSettingsChange}
        />
      </label>
    </div>

    <div class="flex items-end gap-2">
      <Button on:click={handleCycle} disabled={isCycling}>
        {#if isCycling}
          Cycling...
        {:else}
          Cycle Pen Position
        {/if}
      </Button>
    </div>

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
{/if}

