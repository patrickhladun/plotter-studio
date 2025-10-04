# Plotter Studio Monorepo

This repository now groups the Plotter Studio API service and web dashboard inside a single workspace.

## Project layout

- `apps/api` – FastAPI service powering the Plotter Studio endpoints. Refer to its README for Raspberry Pi deployment instructions.
- `apps/dashboard` – Svelte + Vite dashboard that talks to the API and renders the SVG workspace UI.

## Requirements

- Node.js 18+ and [pnpm](https://pnpm.io/) for the dashboard.
- Python 3.11+ for the API tooling.

## Raspberry Pi install

Follow these steps on your Raspberry Pi to deploy the API and bundle the dashboard so it is reachable from any device on your local network.

1. Run the installer (clones `patrickhladun/plotter-studio`, creates a Python virtualenv, builds the dashboard, and copies it next to the API):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/patrickhladun/plotter-studio/main/install.sh | bash
   ```
2. Start the combined API + dashboard server:
   ```bash
   plotterstudio run
   ```
   The installer adds `plotterstudio` to your PATH (with a legacy `sdraw` shim); it binds to `0.0.0.0:2222` by default so LAN devices can reach it.
3. Open the dashboard from any computer/phone on the same network: `http://<pi-address>:2222`.
   By default TLS is disabled; to enable HTTPS rerun the installer with `PLOTTERSTUDIO_ENABLE_TLS=1`. Once enabled you can also visit `https://<pi-address>:2222`.
   Use the **File Manager** panel to upload SVGs, preview them on the canvas, delete unwanted files, or start a plot directly from stored artwork.

### Customising the install

- To target another fork or branch:
  ```bash
  REPO_URL=https://github.com/your-org/plotter-studio.git \
  REPO_REF=feature-branch \
  bash <(curl -fsSL https://raw.githubusercontent.com/patrickhladun/plotter-studio/main/install.sh)
  ```
- The installer pulls the official Axidraw API zip (which provides `axicli`). If you want the legacy `axi` Python helpers, install them manually later (e.g. via `pip install --upgrade "git+https://github.com/evil-mad/axi.git"`).
- SVG uploads are stored in `${PLOTTERSTUDIO_DATA_DIR:-$HOME/plotter-studio/uploads}` (the installer also writes the legacy `SYNTHDRAW_DATA_DIR` variable for compatibility).
- TLS certificates are generated automatically with [`mkcert`](https://github.com/FiloSottile/mkcert) when available. Disable this by setting `PLOTTERSTUDIO_ENABLE_TLS=0` before running the installer.

## Frontend commands

From the repository root:

```bash
pnpm install
pnpm dev:dashboard
```

The dev script proxies to `pnpm --filter dashboard dev`, so you get hot reloads at <http://localhost:5173>. Further scripts:

- `pnpm build:dashboard` – production build to `apps/dashboard/dist`.
- `pnpm preview:dashboard` – serve the built assets.
- `pnpm lint:dashboard` – run `svelte-check`.

The dashboard expects the API to be reachable at `http://localhost:2222` during development; adjust `apps/dashboard/src/lib/rpiApi.ts` if your backend runs elsewhere. Set `VITE_API_BASE_URL` in `apps/dashboard/.env.local` when running `pnpm dev:dashboard` to target a remote API.

## Keeping the server running

Running `plotterstudio run` directly ties the process to your terminal. Use one of these patterns if you want the API to keep running while you close the laptop or disconnect SSH:

- **tmux / screen** – start a multiplexer session (`tmux`, then run `plotterstudio run`). Detach with `Ctrl+B`, `D` and reattach later with `tmux attach`.
- **Background job** – launch `plotterstudio run --host 0.0.0.0 --port 2222 >/home/<user>/plotter-studio/plotterstudio.log 2>&1 &` followed by `disown` so it survives logout. Tail logs via `tail -f ~/plotter-studio/plotterstudio.log`.
- **systemd (user service)** – create `~/.config/systemd/user/plotterstudio.service` pointing to the command above and enable it with `systemctl --user enable --now plotterstudio.service`. The service restarts on boot and stays up without an interactive shell.

Choose whichever fits your workflow; all three keep the web dashboard reachable at `http://<pi-address>:2222` even after you disconnect.

## API commands

Change into `apps/api` and use the existing CLI wrappers (`run.sh`, `install.sh`, etc.) or run the FastAPI app with uvicorn, e.g.

```bash
cd apps/api
poetry install  # or pip install -r requirements.txt
uvicorn main:app --reload
```

Consult `apps/api/README.md` for Raspberry Pi deployment instructions.
