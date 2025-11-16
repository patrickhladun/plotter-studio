<script lang="ts">
  import CanvasWorkspace from './components/Canvas/CanvasWorkspace.svelte';
  import SvgLoader from './components/SvgLoader/SvgLoader.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import ToastHost from './components/ToastHost.svelte';

  let svgContent: string | null = null;
  let showSidebar = true;
  let mobileSvgRef: HTMLDivElement | null = null;

  const handleSvgLoad = (event: CustomEvent<string>) => {
    svgContent = event.detail;
  };
  const toggleSidebar = () => {
    showSidebar = !showSidebar;
  };

  const normalizeMobileSvg = () => {
    if (!mobileSvgRef) return;
    const svg = mobileSvgRef.querySelector('svg');
    if (!svg) return;
    
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    svg.style.width = '100%';
    svg.style.height = '100%';
    svg.style.maxWidth = '100%';
    svg.style.maxHeight = '100%';
    svg.style.display = 'block';
  };

  $: if (svgContent && mobileSvgRef) {
    // Use setTimeout to ensure DOM is updated
    setTimeout(normalizeMobileSvg, 0);
  }
</script>

<div class="font-sans flex min-h-screen overflow-hidden">
  <div class="md:hidden fixed bottom-4 left-1/2 z-20 -translate-x-1/2">
    <button
      class="rounded bg-neutral-800 px-4 py-2 text-xs font-semibold text-neutral-200 shadow"
      type="button"
      on:click={toggleSidebar}
    >
      {showSidebar ? 'Show Canvas' : 'Show Controls'}
    </button>
  </div>
  <div class={`${showSidebar ? 'flex' : 'hidden md:flex'} flex-shrink-0`}>
    <Sidebar on:preview={handleSvgLoad} />
  </div>
  <main
    class={`flex-1 flex flex-col overflow-hidden transition-all duration-200 ${
      showSidebar ? 'hidden md:flex' : 'flex'
    }`}
  >
    <!-- Desktop: Full canvas with rulers and zoom -->
    <div class="hidden md:flex flex-1">
      <CanvasWorkspace {svgContent} />
    </div>
    <!-- Mobile: Simple fitted image -->
    <div class="md:hidden flex-1 bg-neutral-200 flex items-center justify-center p-4">
      {#if svgContent}
        <div class="w-full h-full flex items-center justify-center mobile-svg-container" bind:this={mobileSvgRef}>
          {@html svgContent}
        </div>
      {:else}
        <p class="text-neutral-500 text-sm">No SVG loaded</p>
      {/if}
    </div>
  </main>
  <ToastHost />
</div>

<style>
  :global(.mobile-svg-container svg) {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    display: block;
  }
</style>
