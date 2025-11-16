<script lang="ts">
  import { filesApi, type PlotSettings } from '../../lib/filesApi';
  import { showCommandToast, pushToast } from '../../lib/toastStore';

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
      
      console.log('[StartPlot] Plot settings being sent:', plotSettings);
      console.log('[StartPlot] Model in settings:', plotSettings.model);
      const payload = await filesApi.plot(selectedFile, plotSettings);

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
        pushToast(`Plot completed immediately for ${selectedFile}${summary}`, { tone: 'success' });
        if (onPlotComplete) onPlotComplete(payload);
        if (onStatusPoll) onStatusPoll();
        if (payload && typeof payload.cmd === 'string') {
          showCommandToast('Plot command (offline)', payload.cmd);
        }
        return;
      }

      if (payload && typeof payload.cmd === 'string') {
        showCommandToast(`Plot command${pid ? ` (pid ${pid})` : ''}`, payload.cmd);
      }
      const pidLabel = pid ? ` (pid ${pid})` : '';
      pushToast(`Plot started for ${selectedFile}${pidLabel}`, { tone: 'success' });
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

