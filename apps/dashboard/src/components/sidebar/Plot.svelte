<script lang="ts">
  import StartPlot from '../actions/StartPlot.svelte';
  import Status from '../actions/Status.svelte';
  import type { PlotSettings } from '../../lib/filesApi';

  export let selectedFile: string = '';
  export let plotSettings: PlotSettings;
  export let plotProgress: number | null = null;
  export let plotElapsedSeconds: number | null = null;
  export let plotDistanceMm: number | null = null;
  export let previewTimeSeconds: number | null = null;
  export let previewDistanceMm: number | null = null;
  export let plotting: boolean = false;
  export let plotRunning: boolean = false;
  export let rotating: boolean = false;
  export let stopping: boolean = false;

  import { createEventDispatcher } from 'svelte';
  
  const dispatch = createEventDispatcher<{
    plotStart: void;
    plotComplete: any;
    plotError: string;
    statusPoll: void;
    stopPlot: void;
  }>();

  const handleStopPlot = () => {
    dispatch('stopPlot');
  };
</script>

{#if selectedFile}
  <div class="space-y-3 border-t border-neutral-700 pt-4">
    <Status
      onRefresh={() => dispatch('statusPoll')}
      loading={false}
      {plotProgress}
      {plotElapsedSeconds}
      {plotDistanceMm}
      {previewTimeSeconds}
      {previewDistanceMm}
    />

    <div class="flex flex-wrap gap-2">
      <StartPlot
        selectedFile={selectedFile}
        plotSettings={plotSettings}
        plotting={plotting}
        plotRunning={plotRunning}
        rotating={rotating}
        onPlotStart={() => dispatch('plotStart')}
        onPlotComplete={(payload) => dispatch('plotComplete', payload)}
        onPlotError={(error) => dispatch('plotError', error)}
        onStatusPoll={() => dispatch('statusPoll')}
      />
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
  </div>
{:else}
  <div class="space-y-3 border-t border-neutral-700 pt-4">
    <p class="text-neutral-400 text-xs">Select a file to view plotting controls and settings.</p>
  </div>
{/if}

