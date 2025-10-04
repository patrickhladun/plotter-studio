<script lang="ts">
  import CanvasWorkspace from './components/Canvas/CanvasWorkspace.svelte';
  import SvgLoader from './components/SvgLoader/SvgLoader.svelte';
  import FileManager from './components/FileManager.svelte';

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
  <aside
    class={`bg-neutral-700 space-y-4 transition-all duration-200 ${
      showSidebar ? 'w-full md:w-96' : 'w-0 md:w-96 md:block'
    } ${showSidebar ? 'block' : 'hidden md:block'} overflow-hidden`}
  >
    <FileManager on:preview={handleSvgLoad} />
  </aside>
  <main
    class={`flex-1 flex flex-col overflow-hidden transition-all duration-200 ${
      showSidebar ? 'hidden md:flex' : 'flex'
    }`}
  >
    <CanvasWorkspace {svgContent} />
  </main>
</div>
