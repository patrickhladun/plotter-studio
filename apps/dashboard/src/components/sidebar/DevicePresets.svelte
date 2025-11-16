<script lang="ts">
  import type { DeviceSettings } from '../../lib/filesApi';
  import { createEventDispatcher } from 'svelte';
  import { NEXTDRAW_MODEL_NUMBERS, NEXTDRAW_MODEL_MAP, DEFAULT_MODEL_NUMBER } from '../../lib/nextdrawCommands';

  export let selectedDeviceProfile: string = '';
  export let availableDeviceProfiles: { name: string; settings: DeviceSettings; protected?: boolean }[] = [];
  export let newDeviceName: string = '';
  export let deviceNextdrawModel: number = DEFAULT_MODEL_NUMBER;
  export let deviceAxicliPath: string = '';
  export let deviceHomeOffsetX: number = 0;
  export let deviceHomeOffsetY: number = 0;
  export let deviceNotes: string = '';
  export let devicePenliftMode: number = 1;
  export let deviceNoHoming: boolean = false;

  const dispatch = createEventDispatcher<{
    presetChange: string;
    presetSave: void;
    presetDelete: void;
    modelChange: number;
    penliftChange: number;
    settingsChange: void;
  }>();

  const handlePresetChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? target.value : selectedDeviceProfile;
    dispatch('presetChange', value);
  };

  const handlePresetSave = () => {
    dispatch('presetSave');
  };

  const handlePresetDelete = () => {
    dispatch('presetDelete');
  };

  const handleModelChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? Number(target.value) : DEFAULT_MODEL_NUMBER;
    if (!isNaN(value) && value >= 1 && value <= 10) {
      dispatch('modelChange', value);
    }
  };

  const handlePenliftChange = (event: Event) => {
    const target = event.currentTarget as HTMLSelectElement | null;
    const value = target ? Number(target.value) : devicePenliftMode;
    dispatch('penliftChange', value);
  };

  const handleSettingsChange = () => {
    dispatch('settingsChange');
  };
</script>

<div class="space-y-4 text-xs text-neutral-200 border-t border-neutral-700 pt-4">
  <div class="space-y-2">
    <label class="flex flex-col gap-1">
      <h2 class="text-xl font-semibold mb-2 text-white">Device preset</h2>
      <select
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        value={selectedDeviceProfile}
        on:change={handlePresetChange}
      >
        {#each availableDeviceProfiles as profile}
          <option value={profile.name}>{profile.name}</option>
        {/each}
      </select>
    </label>
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
      <input
        type="text"
        class="flex-1 rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        placeholder="Preset name"
        bind:value={newDeviceName}
      />
      <button
        class="bg-blue-500 hover:bg-blue-400 text-white text-xs font-medium px-3 py-1 rounded"
        type="button"
        on:click={handlePresetSave}
      >
        Save device
      </button>
      {#if availableDeviceProfiles.find((profile) => profile.name === selectedDeviceProfile)?.protected !== true}
        <button
          class="bg-red-500 hover:bg-red-400 text-white text-xs font-medium px-3 py-1 rounded"
          type="button"
          on:click={handlePresetDelete}
        >
          Delete device
        </button>
      {/if}
    </div>
    <label class="flex flex-col gap-1">
      Plotter model
      <select
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        value={deviceNextdrawModel}
        on:change={handleModelChange}
      >
        {#each NEXTDRAW_MODEL_NUMBERS as modelNumber}
          <option value={modelNumber}>{NEXTDRAW_MODEL_MAP[modelNumber]}</option>
        {/each}
      </select>
    </label>
  </div>

  <div class="grid gap-3 sm:grid-cols-2">
    <label class="flex flex-col gap-1">
      <span>NextDraw/AxiCLI path</span>
      <input
        type="text"
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        bind:value={deviceAxicliPath}
        on:change={handleSettingsChange}
      />
    </label>
    <label class="flex flex-col gap-1">
      <span>Home offset X (mm)</span>
      <input
        type="number"
        step="0.1"
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        bind:value={deviceHomeOffsetX}
        on:change={handleSettingsChange}
      />
    </label>
    <label class="flex flex-col gap-1">
      <span>Home offset Y (mm)</span>
      <input
        type="number"
        step="0.1"
        class="rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
        bind:value={deviceHomeOffsetY}
        on:change={handleSettingsChange}
      />
    </label>
  </div>
  <label class="flex flex-col gap-1">
    <span>Notes</span>
    <textarea
      class="min-h-[80px] rounded bg-neutral-800 border border-neutral-500 px-2 py-1 text-neutral-100"
      bind:value={deviceNotes}
      on:change={handleSettingsChange}
    />
  </label>
  <label class="flex items-center gap-2">
    <input type="checkbox" bind:checked={deviceNoHoming} on:change={handleSettingsChange} />
    <span>Skip homing before plots (`--no_homing`)</span>
  </label>
</div>

