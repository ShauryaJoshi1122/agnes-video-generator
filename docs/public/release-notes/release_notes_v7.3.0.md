# Release v7.3.0 — Durable Local Install and Agent-Friendly Startup for AI Video Generation

> Release date: 2026-10-21

## Overview

v7.3.0 makes the local installation of this **free AI short-video generator** durable: everything mutable
(runtime, API key config, workspace, logs) now lives in one data root instead of inside the npm package
directory, Python dependencies are installed once instead of on every start, and the launcher gains
`--detach` / `--json` / `--print-paths` so scripts and AI agents can start the service and get a
machine-readable result. It also adds `AGNES_WORKING_DIR` for relocating the default workspace and a
`has_key` field on `GET /api/config` for tooling.

## Usage

From v7.2.0 (source):

```bash
git pull
./start.sh
```

Docker users: `docker pull ghcr.io/lcy362/free-short-video:7.3.0` (then `docker compose up -d` to
recreate the container).

npm users: `npx free-short-video` or `npm install -g free-short-video`.

### Upgrading notes

- **Where your data lives changed for npm / npx installs.** Runtime and data now sit in `~/.agnes-video`
  by default (`AGNES_HOME` or `--home <dir>` overrides it): `venv/`, `config/`, `workspace/`, `logs/`.
  Previously they lived inside the package directory, which for `npx` is an npm cache folder — an
  `npm cache clean` or a version bump could take them with it.
- **Your existing settings are migrated automatically.** On the first run, a `.agnes_config` found in the
  package directory is copied into the new data root, so the configured API key and preferences carry
  over. Nothing else is moved; videos produced earlier stay where they were written.
- Docker and source installations are unaffected (they keep their existing mount points / project
  directory).

## What's New

### Features & Improvements

- **Durable, cache-proof local install.** The launcher keeps its virtualenv, configuration, workspace and
  logs under one data root (`~/.agnes-video` by default, `AGNES_HOME` / `--home` to move it). Clearing
  the npm cache or upgrading the package no longer re-downloads every Python dependency, and generated
  videos no longer live inside a package folder.
- **One-time dependency install.** Python dependencies are installed once and reused; `pip` runs again
  only when `requirements.txt` actually changed (verified by a sha256 fingerprint). Later starts skip the
  network entirely, so the service can come up offline.
- **Script and AI-agent friendly startup.** `--detach` starts the service in the background and exits
  once it answers; `--json` prints a machine-readable result (`ok`, `ready`, `pid`, `base`, `home`,
  `venv`, `workspace`, `log`); `--print-paths` shows where each part lives. Useful for automation,
  editor tasks and agent workflows that need the service without taking over a terminal.
- **Relocatable default workspace.** `AGNES_WORKING_DIR` now decides where the default workspace points,
  so the production install can keep generated media on a different disk or folder.
- **`has_key` on `GET /api/config`.** Tooling can tell whether an API key is configured without parsing
  the masked key prefix.

### Bug Fixes

- Failed asset imports no longer expose internal error details to the caller.
- Watermark fallback paths and ffmpeg overlay failures are now logged with stack traces, so a missing
  font or a broken overlay can be diagnosed from the log instead of an unexplained watermark.

---

**Compatibility:** no API breaks. Existing `.env` files, workspaces configured in the Web UI, and keys
supplied through `AGNES_API_KEY` keep working; environment keys still use the single global domain.
