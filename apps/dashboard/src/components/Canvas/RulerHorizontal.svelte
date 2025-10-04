<script lang="ts">
  export let offsetPx: number;
  export let scale: number;

  const STEP_MM = 10;
  const MAJOR_STEP_MM = 50;
  const RANGE_MM = 1000;

  const marks: number[] = [];
  for (let mm = -RANGE_MM; mm <= RANGE_MM; mm += STEP_MM) {
    marks.push(mm);
  }
</script>

<div class="relative h-full w-full overflow-hidden bg-gray-100 text-[10px] text-gray-500">
  {#each marks as mm}
    <div
      class={`absolute border-l border-gray-400 ${mm % MAJOR_STEP_MM === 0 ? 'opacity-80' : 'opacity-50'}`}
      style={`left: ${mm * scale - offsetPx}px; top: 0; bottom: 0;`}
    >
      {#if mm % MAJOR_STEP_MM === 0}
        <span class="absolute top-0 left-1 select-none text-[10px]">{mm}</span>
      {/if}
    </div>
  {/each}
</div>
