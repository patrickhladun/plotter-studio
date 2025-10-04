<script lang="ts">
  export let disabled = false;
  export let type: 'button' | 'submit' | 'reset' = 'button';
</script>

<button
  class="bg-blue-400 py-1 px-2 text-xs rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
  type={type}
  disabled={disabled}
  on:click
>
  <slot />
</button>
