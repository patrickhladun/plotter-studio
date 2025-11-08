# Plotter Studio API

Plotter Studio is a FastAPI server.

## Installation

```
curl -s https://raw.githubusercontent.com/patrickhladun/plotter-studio/main/install.sh | bash
```

## Versioning

- Application version source of truth is defined in `pyproject.toml`.
- The API reports its current version at runtime via the `/version` endpoint and the FastAPI docs metadata.
- Bump both places by running `sed -i '' "s/0.1.0/<new version>/" pyproject.toml version.py` on macOS, or update the two files manually before deploying.

## Raspberry Pi setup

- Run the installer from your Pi: `curl -s https://raw.githubusercontent.com/patrickhladun/plotter-studio/main/install.sh | bash`. It will clone the repo into `~/plotter-studio`, create a virtualenv, and install the package.
- The installer links the CLI to `~/.local/bin/plotterstudio` (and keeps a legacy `sdraw` shim), attempts to drop a sudo-backed symlink in `/usr/local/bin`, and updates your shell `PATH`. Restart your terminal (or run `source ~/.profile` for bash, `source ~/.zshenv && source ~/.zshrc` for zsh) before using the command.
- During installation `mkcert` is installed (if missing) and a TLS certificate is generated for the Pi’s primary IP/hostname. Override the Common Name with `PLOTTERSTUDIO_TLS_CN=plotter.local install.sh` or skip automatic TLS with `PLOTTERSTUDIO_ENABLE_TLS=0 ...`.
- The generated certificate/key live in `~/plotter-studio/certs/` and their paths are stored in `~/plotter-studio/.env`; that file is sourced by the CLI, `run.sh`, and the systemd unit.
- The installer attempts to locate the `axicli` executable (including pyenv environments) and records it in `.env`. Override with `PLOTTERSTUDIO_AXICLI=/full/path/to/axicli` if you prefer a different binary.
- After installation run `which plotterstudio` (or `command -v plotterstudio`) to confirm the CLI is visible.
- Start the server anywhere with `plotterstudio` (or `plotterstudio run`). The CLI automatically loads host, port, log level, and TLS paths from `~/plotter-studio/.env`; use flags like `--reload`, `--no-ssl`, or custom `--ssl-*` paths when needed.
- Print the derived runtime configuration with `plotterstudio show-config` if you want to confirm which certificate and port will be used.
- To update an existing install, run `~/plotter-studio/update.sh`. The script pulls `origin/main` and reinstalls the package inside the virtualenv.
- `~/plotter-studio/run.sh` remains as a convenience wrapper that activates the venv, loads `.env`, and forwards all arguments to the CLI.

## Optional systemd service

- Copy `deploy/plotterstudio@.service` to `/etc/systemd/system/` on the Pi. Enable it as your user, e.g. `sudo systemctl enable --now plotterstudio@pi`.
- Override configuration by editing the service file or creating a drop-in at `/etc/systemd/system/plotterstudio@pi.service.d/override.conf`.
- The unit reads `~/plotter-studio/.env`; adjust certificate paths or defaults there and restart the service.

## HTTPS options

- **Local mkcert TLS (default)** – the installer provisions a certificate for the chosen IP/hostname and configures the CLI to use it. Install mkcert on every client machine and run `mkcert -install` so browsers trust the generated CA.
- **Public domain + reverse proxy** – point DNS (e.g. `pi.example.com`) at your router, forward port 443 to the Pi, and terminate TLS with Caddy or Nginx (Caddy example: `pi.example.com { reverse_proxy localhost:2222 }`).
- **Tunneled HTTPS** – expose the local HTTP server via Cloudflare Tunnel, Tailscale Funnel, etc., for managed HTTPS without opening ports.

## Cleanup

- To completely remove the install, run

```
~/plotter-studio/cleanup.sh --yes
```

It deletes the application directory, removes the CLI symlinks in `~/.local/bin` and `/usr/local/bin`, and prunes the PATH lines added by the installer. Omit `--yes` to receive a confirmation prompt before deletion.
