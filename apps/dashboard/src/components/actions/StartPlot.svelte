<script lang="ts">
  import { type PlotSettings } from '../../lib/filesApi';
  import { pushToast } from '../../lib/toastStore';
  import { buildPlotCommand } from '../../lib/model';
  import { executeCommand } from '../../lib/commandExecutor';

  export let selectedFile: string = '';
  export let plotSettings: PlotSettings;
  export let plotting: boolean = false;
  export let plotRunning: boolean = false;
  export let rotating: boolean = false;
  
  // Callbacks for parent component
  export let onPlotStart: (() => void) | undefined = undefined;
  export let onPlotComplete: ((payload: any) => void) | undefined = undefined;
  export let onPlotError: ((error: string) => void) | undefined = undefined;
  export let onStatusPoll: (() => void) | undefined = undefined;

  const handlePlot = async () => {
    if (!selectedFile) {
      pushToast('Select a file before starting a plot.', { tone: 'error' });
      return;
    }

    try {
      if (onPlotStart) onPlotStart();
      
      // Build the complete plot command using getFlag()
      const command = buildPlotCommand(selectedFile, {
        s_down: plotSettings.s_down,
        s_up: plotSettings.s_up,
        p_down: plotSettings.p_down,
        p_up: plotSettings.p_up,
        handling: plotSettings.handling,
        speed: plotSettings.speed,
        penlift: plotSettings.penlift,
        no_homing: plotSettings.no_homing,
        layer: plotSettings.layer,
      });
      
      console.log('[StartPlot] Plot command:', command);
      
      // Execute the command via /plot endpoint (same as other actions)
      const result = await executeCommand(command, 'Plot');
      
      if (!result.success) {
        const errorMessage = result.error || 'Plot failed';
        pushToast(errorMessage, { tone: 'error' });
        if (onPlotError) onPlotError(errorMessage);
        return;
      }
      
      const payload = result.payload;

      // Show success message
      const stdout = payload && typeof payload.stdout === 'string' ? payload.stdout : null;
      const inferredMessage = stdout && stdout.trim().length > 0
        ? stdout.trim().split('\n')[0]
        : `Plot started for ${selectedFile}`;
      pushToast(inferredMessage, { tone: 'success' });
      
      if (onPlotComplete) onPlotComplete(payload);
      if (onStatusPoll) onStatusPoll();
    } catch (error) {
      console.error('Plot failed', error);
      const message = error instanceof Error ? error.message : 'Plot start failed';
      pushToast(message, { tone: 'error' });
      if (onPlotError) onPlotError(message);
    }
  };
</script>

<button
  class="bg-green-500 py-1 px-2 text-xs rounded cursor-pointer hover:bg-green-400 disabled:opacity-50 disabled:cursor-not-allowed"
  type="button"
  on:click={handlePlot}
  disabled={plotting || rotating || plotRunning}
>
  {#if plotting}
    Starting…
  {:else}
    Start Plot
  {/if}
</button>

