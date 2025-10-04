<script lang="ts">
  import { afterUpdate, onMount } from 'svelte';

  export let svgContent: string | null = null;
  export let width: number;
  export let height: number;

  let contentRef: HTMLDivElement | null = null;

  const parseLengthToPx = (value: string | null | undefined): number | null => {
    if (!value) {
      return null;
    }

    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }

    const match = trimmed.match(/^([+-]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)$/);
    if (!match) {
      return null;
    }

    const numeric = Number(match[1]);
    if (!Number.isFinite(numeric)) {
      return null;
    }

    const unit = match[2].toLowerCase();
    const factors: Record<string, number> = {
      mm: 96 / 25.4,
      millimeter: 96 / 25.4,
      millimeters: 96 / 25.4,
      cm: 96 / 2.54,
      centimeter: 96 / 2.54,
      centimeters: 96 / 2.54,
      m: 96 * 39.37007874,
      meter: 96 * 39.37007874,
      meters: 96 * 39.37007874,
      in: 96,
      inch: 96,
      inches: 96,
      pt: 96 / 72,
      pc: 16,
      px: 1,
      q: (96 / 25.4) / 4,
    };

    if (!unit) {
      return numeric;
    }

    const factor = factors[unit];
    if (!factor) {
      return null;
    }

    return numeric * factor;
  };

  const normalizeSvgSizing = () => {
    if (!contentRef) {
      return;
    }

    const svg = contentRef.querySelector('svg');
    if (!svg) {
      return;
    }

    svg.setAttribute('preserveAspectRatio', svg.getAttribute('preserveAspectRatio') || 'xMidYMid meet');

    const hasViewBox = svg.hasAttribute('viewBox') && svg.getAttribute('viewBox')?.trim();
    if (!hasViewBox) {
      const widthAttr = svg.getAttribute('width');
      const heightAttr = svg.getAttribute('height');
      const widthPx = parseLengthToPx(widthAttr);
      const heightPx = parseLengthToPx(heightAttr);
      if (widthPx && heightPx) {
        svg.setAttribute('viewBox', `0 0 ${widthPx} ${heightPx}`);
      }
    }

    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    const style = svg.style;
    style.width = '100%';
    style.height = '100%';
    style.maxWidth = '100%';
    style.maxHeight = '100%';
    style.display = 'block';
    style.objectFit = 'contain';
  };

  onMount(normalizeSvgSizing);
  afterUpdate(normalizeSvgSizing);
</script>

<div
  id="canvas"
  class="bg-white shadow border flex items-center justify-center overflow-hidden"
  style={`width: ${width}px; height: ${height}px;`}
>
  {#if svgContent}
    <div class="w-full h-full flex items-center justify-center" bind:this={contentRef}>
      {@html svgContent}
    </div>
  {:else}
    <p class="text-gray-500">No SVG loaded</p>
  {/if}
</div>

<style>
  :global(#canvas svg) {
    width: 100%;
    height: 100%;
    display: block;
  }

  :global(#canvas svg) {
    object-fit: contain;
  }
</style>
