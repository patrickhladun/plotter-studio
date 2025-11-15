import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

const parsePort = (value: string | undefined, fallback: number) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

const serverHost = process.env.DASHBOARD_HOST || "0.0.0.0";
const serverPort = parsePort(process.env.DASHBOARD_PORT, 2121);

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: serverPort,
    host: serverHost,
  },
  preview: {
    port: serverPort,
    host: serverHost,
  },
});
