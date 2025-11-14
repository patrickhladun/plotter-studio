<script lang="ts">
  import Button from '../Button/Button.svelte';
  import { API_BASE_URL } from '../../lib/rpiApi';

  let statusData: any = null;
  let statusError: string | null = null;
  let loading = false;

  const fetchStatus = async () => {
    statusError = null;
    statusData = null;
    loading = true;

    try {
      const response = await fetch(`${API_BASE_URL}/plot/status`);
      if (!response.ok) {
        statusError = `Error: ${response.statusText}`;
        console.error('API error:', response.statusText);
        return;
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        statusData = await response.json();
        console.log('Status:', statusData);
      } else {
        const text = await response.text();
        statusError = text || 'Unknown response format';
        console.log('Status text:', text);
      }
    } catch (error) {
      statusError = error instanceof Error ? error.message : 'Failed to fetch status';
      console.error('API error:', error);
    } finally {
      loading = false;
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (seconds === null || !Number.isFinite(seconds)) return '—';
    const totalSeconds = Math.round(seconds);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  };

  const formatDistance = (mm: number | null) => {
    if (mm === null || !Number.isFinite(mm)) return '—';
    if (mm >= 1000) return `${(mm / 1000).toFixed(2)} m`;
    if (mm >= 10) return `${(mm / 10).toFixed(1)} cm`;
    return `${mm.toFixed(1)} mm`;
  };
</script>

<div class="space-y-2">
  <Button on:click={fetchStatus} disabled={loading}>
    {loading ? 'Refreshing...' : 'Refresh Status'}
  </Button>

  {#if statusError}
    <div class="text-red-400 text-xs p-2 bg-red-900/20 rounded">
      {statusError}
    </div>
  {/if}

  {#if statusData}
    <div class="text-xs text-neutral-300 p-3 bg-neutral-800/60 rounded space-y-1">
      <div class="flex justify-between">
        <span class="text-neutral-400">Status:</span>
        <span class={statusData.running ? 'text-green-400 font-semibold' : 'text-neutral-300'}>
          {statusData.running ? 'Running' : 'Idle'}
        </span>
      </div>

      {#if statusData.file}
        <div class="flex justify-between">
          <span class="text-neutral-400">File:</span>
          <span class="font-mono">{statusData.file}</span>
        </div>
      {/if}

      {#if statusData.progress !== null && statusData.progress !== undefined}
        <div class="flex justify-between">
          <span class="text-neutral-400">Progress:</span>
          <span>{Math.round(statusData.progress)}%</span>
        </div>
      {/if}

      <div class="flex justify-between">
        <span class="text-neutral-400">Elapsed:</span>
        <span>{formatDuration(statusData.elapsed_seconds)}</span>
      </div>

      <div class="flex justify-between">
        <span class="text-neutral-400">Distance:</span>
        <span>{formatDistance(statusData.distance_mm)}</span>
      </div>

      {#if statusData.error}
        <div class="pt-2 border-t border-neutral-700">
          <span class="text-red-400">Error: {statusData.error}</span>
        </div>
      {/if}
    </div>
  {/if}
</div>
