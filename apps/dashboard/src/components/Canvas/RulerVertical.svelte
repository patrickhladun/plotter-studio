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

<div class="relative w-full h-full overflow-hidden bg-gray-100 text-[10px] text-gray-500">
  {#each marks as mm}
    <div
      class={`absolute border-t border-gray-400 ${mm % MAJOR_STEP_MM === 0 ? 'opacity-80' : 'opacity-50'}`}
      style={`top: ${mm * scale - offsetPx}px; left: 0; right: 0;`}
    >
      {#if mm % MAJOR_STEP_MM === 0}
        <span class="absolute left-1 top-0 select-none text-[10px]">{mm}</span>
      {/if}
    </div>
  {/each}
</div>
