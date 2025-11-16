<script lang="ts">
  import CanvasWorkspace from './components/Canvas/CanvasWorkspace.svelte';
  import SvgLoader from './components/SvgLoader/SvgLoader.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import ToastHost from './components/ToastHost.svelte';

  let svgContent: string | null = null;
  let showSidebar = true;

  const handleSvgLoad = (event: CustomEvent<string>) => {
    svgContent = event.detail;
  };
  const toggleSidebar = () => {
    showSidebar = !showSidebar;
  };
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
    <CanvasWorkspace {svgContent} />
  </main>
  <ToastHost />
</div>
