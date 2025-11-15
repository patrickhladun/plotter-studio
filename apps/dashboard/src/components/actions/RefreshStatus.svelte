<script lang="ts">
  export let onRefresh: (() => void) | undefined = undefined;
  export let loading: boolean = false;

  const handleRefresh = () => {
    if (onRefresh) {
      onRefresh();
    }
  };
</script>

<button
  class="text-blue-300 hover:text-blue-200 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
  type="button"
  on:click={handleRefresh}
  disabled={loading}
>
  {#if loading}
    Refreshing…
  {:else}
    Refresh status
  {/if}
</button>

