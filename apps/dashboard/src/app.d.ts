/// <reference types="svelte" />
/// <reference types="vite/client" />

declare module '*.svelte' {
  import type { SvelteComponentTyped } from 'svelte';
  export default class Component extends SvelteComponentTyped<Record<string, any>> {}
}

export {};
