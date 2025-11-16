import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import os from 'os';

const parsePort = (value: string | undefined, fallback: number) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

const serverHost = process.env.DASHBOARD_HOST || "0.0.0.0";
const serverPort = parsePort(process.env.DASHBOARD_PORT, 2121);
const apiPort = parsePort(process.env.PLOTTERSTUDIO_PORT, 2222);

// Detect network IP for proxy target
// Since localhost doesn't work on this system, use the network IP
let apiHost = process.env.PLOTTERSTUDIO_NETWORK_IP || "127.0.0.1";
if (apiHost === "127.0.0.1") {
  try {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
      for (const iface of interfaces[name] || []) {
        if (iface.family === 'IPv4' && !iface.internal && iface.address) {
          apiHost = iface.address;
          console.log(`[Vite Config] Using network IP ${apiHost} for API proxy`);
          break;
        }
      }
      if (apiHost !== "127.0.0.1") break;
    }
  } catch (e) {
    console.warn('[Vite Config] Could not detect network IP, using 127.0.0.1');
  }
}

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: serverPort,
    host: serverHost,
    proxy: {
      "/files": {
        target: `http://${apiHost}:${apiPort}`,
        changeOrigin: true,
        secure: false,
        ws: false,
        timeout: 60000, // 60 second timeout for file uploads
        configure: (proxy, _options) => {
          proxy.on('error', (err, req, res) => {
            console.error('[Vite Proxy] ERROR:', err.message);
            console.error('[Vite Proxy] Request:', req.method, req.url);
            console.error('[Vite Proxy] Error details:', err);
            if (res && !res.headersSent) {
              res.writeHead(500, { 'Content-Type': 'text/plain' });
              res.end('Proxy error: ' + err.message);
            }
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('[Vite Proxy] → Proxying:', req.method, req.url, '→', `http://${apiHost}:${apiPort}${req.url}`);
            console.log('[Vite Proxy] Headers:', req.headers);
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('[Vite Proxy] ← Response:', req.method, req.url, '→', proxyRes.statusCode);
          });
        },
      },
      "/plot": {
        target: `http://${apiHost}:${apiPort}`,
        changeOrigin: true,
        secure: false,
        ws: false,
      },
      "/status": {
        target: `http://${apiHost}:${apiPort}`,
        changeOrigin: true,
        secure: false,
        ws: false,
      },
      "/version": {
        target: `http://${apiHost}:${apiPort}`,
        changeOrigin: true,
        secure: false,
        ws: false,
      },
      "/settings": {
        target: `http://${apiHost}:${apiPort}`,
        changeOrigin: true,
        secure: false,
        ws: false,
      },
      "/session": {
        target: `http://${apiHost}:${apiPort}`,
        changeOrigin: true,
        secure: false,
        ws: false,
      },
    },
  },
  preview: {
    port: serverPort,
    host: serverHost,
  },
});
