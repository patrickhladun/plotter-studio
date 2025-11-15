<script lang="ts">
  import { fly } from 'svelte/transition';
  import { dismissToast, toasts } from '../lib/toastStore';

  const toneStyles: Record<string, string> = {
    info: 'border-blue-400 text-blue-50',
    success: 'border-green-400 text-green-50',
    error: 'border-red-400 text-red-50',
  };
</script>

<div class="pointer-events-none fixed top-3 right-3 z-50 flex flex-col gap-2">
  {#each $toasts as toast (toast.id)}
    <div
      class={`pointer-events-auto w-72 rounded border-l-4 bg-neutral-900/90 px-4 py-3 shadow-lg ${toneStyles[toast.tone] ?? toneStyles.info}`}
      transition:fly={{ x: 16, duration: 200 }}
    >
      <div class="flex items-start justify-between gap-2">
        <div class="text-sm font-semibold leading-tight">{toast.message}</div>
        <button
          class="text-xs text-current/70 hover:text-current"
          type="button"
          aria-label="Dismiss toast"
          on:click={() => dismissToast(toast.id)}
        >
          ×
        </button>
      </div>
      {#if toast.detail}
        <pre class="mt-1 rounded bg-neutral-800/80 px-2 py-1 text-[11px] font-mono text-neutral-100 whitespace-pre-wrap break-words">
{toast.detail}
        </pre>
      {/if}
    </div>
  {/each}
</div>
