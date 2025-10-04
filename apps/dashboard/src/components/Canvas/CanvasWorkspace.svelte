<script lang="ts">
  import { onMount } from 'svelte';
  import Canvas from './Canvas.svelte';
  import RulerHorizontal from './RulerHorizontal.svelte';
  import RulerVertical from './RulerVertical.svelte';

  export let svgContent: string | null = null;

  const RULER_SIZE = 24;
  const BASE_PIXELS_PER_MM = 2;
  const MIN_ZOOM = 0.25;
  const MAX_ZOOM = 6;
  const ZOOM_STEP = 1.1;

  const DEFAULT_SIZE_MM = { width: 210, height: 297 };

  let canvasPosition = { x: 0, y: 0 };
  let isDragging = false;
  let derivedSizeMm = DEFAULT_SIZE_MM;
  let zoom = 1;
  let pixelsPerMm = BASE_PIXELS_PER_MM;
  let canvasWidthPx = derivedSizeMm.width * pixelsPerMm;
  let canvasHeightPx = derivedSizeMm.height * pixelsPerMm;
  let containerRef: HTMLDivElement | null = null;
  let svgSignature: string | null = null;

  const dragState = {
    pointerId: null as number | null,
    start: { x: 0, y: 0 },
    origin: { x: 0, y: 0 },
  };

  const parseLengthToMm = (value: string | null | undefined): number | null => {
    if (!value) return null;
    const match = value.trim().match(/^([+-]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)$/);
    if (!match) return null;
    const numeric = Number(match[1]);
    if (!Number.isFinite(numeric)) return null;
    const unit = match[2].toLowerCase();
    const factors: Record<string, number> = {
      mm: 1,
      millimeter: 1,
      millimeters: 1,
      cm: 10,
      centimeter: 10,
      centimeters: 10,
      m: 1000,
      meter: 1000,
      meters: 1000,
      in: 25.4,
      inch: 25.4,
      inches: 25.4,
      pt: 25.4 / 72,
      pc: 25.4 / 6,
      px: 25.4 / 96,
      q: 0.25,
    };
    if (!unit) return numeric;
    const factor = factors[unit];
    if (!factor) return null;
    return numeric * factor;
  };

  const parseSvgSize = (content: string | null) => {
    if (typeof window === 'undefined' || !content) return DEFAULT_SIZE_MM;

    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(content, 'image/svg+xml');
      const svg = doc.querySelector('svg');
      if (!svg) return DEFAULT_SIZE_MM;

      const widthMm = parseLengthToMm(svg.getAttribute('width'));
      const heightMm = parseLengthToMm(svg.getAttribute('height'));
      if (widthMm && heightMm) {
        return { width: widthMm, height: heightMm };
      }

      const viewBox = svg.getAttribute('viewBox');
      if (viewBox) {
        const parts = viewBox.trim().split(/\s+/);
        if (parts.length === 4) {
          const vbWidth = Number(parts[2]);
          const vbHeight = Number(parts[3]);
          if (Number.isFinite(vbWidth) && Number.isFinite(vbHeight)) {
            const pxToMm = 25.4 / 96;
            return { width: vbWidth * pxToMm, height: vbHeight * pxToMm };
          }
        }
      }
    } catch (error) {
      console.warn('Failed to parse SVG size', error);
    }

    return DEFAULT_SIZE_MM;
  };

  $: derivedSizeMm = parseSvgSize(svgContent);
  $: pixelsPerMm = BASE_PIXELS_PER_MM * zoom;
  $: canvasWidthPx = derivedSizeMm.width * pixelsPerMm;
  $: canvasHeightPx = derivedSizeMm.height * pixelsPerMm;

  $: {
    const signature = svgContent ?? null;
    if (signature !== svgSignature) {
      svgSignature = signature;
      zoom = 1;
      centerView(BASE_PIXELS_PER_MM);
    }
  }

  const handlePointerDown = (event: PointerEvent) => {
    if (event.button !== 0) {
      return;
    }

    dragState.pointerId = event.pointerId;
    dragState.start = { x: event.clientX, y: event.clientY };
    dragState.origin = { ...canvasPosition };

    (event.currentTarget as HTMLDivElement).setPointerCapture(event.pointerId);
    isDragging = true;
  };

  const handlePointerMove = (event: PointerEvent) => {
    if (dragState.pointerId !== event.pointerId) {
      return;
    }

    event.preventDefault();

    const dx = event.clientX - dragState.start.x;
    const dy = event.clientY - dragState.start.y;

    canvasPosition = {
      x: dragState.origin.x + dx,
      y: dragState.origin.y + dy,
    };
  };

  const endDrag = (event: PointerEvent) => {
    if (dragState.pointerId !== event.pointerId) {
      return;
    }

    (event.currentTarget as HTMLDivElement).releasePointerCapture(event.pointerId);
    dragState.pointerId = null;
    isDragging = false;
  };

  const clampZoom = (value: number) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value));

  const computeCenteredPosition = (scale: number) => {
    if (!containerRef) {
      return { x: 0, y: 0 };
    }
    const rect = containerRef.getBoundingClientRect();
    const widthPx = derivedSizeMm.width * scale;
    const heightPx = derivedSizeMm.height * scale;
    return {
      x: (rect.width - widthPx) / 2,
      y: (rect.height - heightPx) / 2,
    };
  };

  const centerView = (scale: number) => {
    canvasPosition = computeCenteredPosition(scale);
  };

  const applyZoom = (targetZoom: number, focusX: number, focusY: number) => {
    const newZoom = clampZoom(targetZoom);
    if (newZoom === zoom) {
      return;
    }

    const oldPixelsPerMm = pixelsPerMm;
    const newPixelsPerMm = BASE_PIXELS_PER_MM * newZoom;

    const canvasX = focusX - canvasPosition.x;
    const canvasY = focusY - canvasPosition.y;

    const worldX = canvasX / oldPixelsPerMm;
    const worldY = canvasY / oldPixelsPerMm;

    zoom = newZoom;

    canvasPosition = {
      x: focusX - worldX * newPixelsPerMm,
      y: focusY - worldY * newPixelsPerMm,
    };
  };

  const handleWheel = (event: WheelEvent) => {
    event.preventDefault();
    if (!containerRef) {
      return;
    }

    const rect = containerRef.getBoundingClientRect();
    const focusX = event.clientX - rect.left;
    const focusY = event.clientY - rect.top;

    const factor = event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
    applyZoom(zoom * factor, focusX, focusY);
  };

  const incrementZoom = (direction: 1 | -1) => {
    if (!containerRef) {
      return;
    }
    const rect = containerRef.getBoundingClientRect();
    const focusX = rect.width / 2;
    const focusY = rect.height / 2;
    const factor = direction === 1 ? ZOOM_STEP : 1 / ZOOM_STEP;
    applyZoom(zoom * factor, focusX, focusY);
  };

  onMount(() => {
    centerView(BASE_PIXELS_PER_MM * zoom);
  });
</script>

<div class="flex flex-col flex-1 bg-neutral-200 overflow-hidden">
  <div class="flex flex-col flex-1">
    <div class="h-[24px] flex overflow-hidden" style={`margin-left: ${RULER_SIZE}px;`}>
      <RulerHorizontal offsetPx={-canvasPosition.x} scale={pixelsPerMm} />
    </div>

    <div class="flex flex-1">
      <div class="w-[24px] overflow-hidden">
        <RulerVertical offsetPx={-canvasPosition.y} scale={pixelsPerMm} />
      </div>

      <div
        class={`relative flex-1 bg-neutral-300 overflow-hidden select-none ${
          isDragging ? 'cursor-grabbing' : 'cursor-grab'
        }`}
        bind:this={containerRef}
        on:pointerdown={handlePointerDown}
        on:pointermove={handlePointerMove}
        on:pointerup={endDrag}
        on:pointercancel={endDrag}
        on:wheel|preventDefault={handleWheel}
      >
        <div
          class="absolute top-2 right-2 z-10 flex items-center gap-2 rounded bg-white/90 px-3 py-1 text-xs text-neutral-700 shadow"
          on:pointerdown|stopPropagation
        >
          <button
            class="px-2 py-1 rounded bg-neutral-200 hover:bg-neutral-300"
            type="button"
            on:click={() => incrementZoom(-1)}
          >
            −
          </button>
          <span class="min-w-[3.5rem] text-center">{Math.round(zoom * 100)}%</span>
          <button
            class="px-2 py-1 rounded bg-neutral-200 hover:bg-neutral-300"
            type="button"
            on:click={() => incrementZoom(1)}
          >
            +
          </button>
          <button
            class="px-2 py-1 rounded bg-neutral-200 hover:bg-neutral-300"
            type="button"
            on:click={() => applyZoom(1, containerRef ? containerRef.clientWidth / 2 : 0, containerRef ? containerRef.clientHeight / 2 : 0)}
          >
            Reset
          </button>
        </div>
        <div class="absolute inset-0">
          <div
            class="absolute"
            style={`left: ${canvasPosition.x}px; top: ${canvasPosition.y}px; width: ${canvasWidthPx}px; height: ${canvasHeightPx}px;`}
          >
            <Canvas {svgContent} width={canvasWidthPx} height={canvasHeightPx} />
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
