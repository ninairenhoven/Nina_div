# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A personal web app for viewing orienteering start lists from Eventor.no (the Norwegian orienteering event system). It shows start times for a fixed set of tracked family members and their club (Oppsal). Deployed at `eventor.fjoven.com`.

## Running locally

```bash
# Windows
start.bat

# Mac/Linux
python app.py
```

The Flask dev server runs on port 5001. Open `http://localhost:5001`.

Requires a `.env` file with:
```
EVENTOR_API_KEY=...
EVENTOR_PERSON_ID=45234
EVENTOR_TRACKED_IDS=1620,1621,4427,44761,45124,45234
```

## Deploying

```bash
bash deploy.sh
```

Copies `app.py`, `requirements.txt`, `ecosystem.config.js`, and `cloudflare/` to `nina@fjoven.com:/var/www/eventor`, installs dependencies in a venv, and restarts via PM2.

**Only deploy when the user explicitly asks.**

## Architecture

There are two independent deployment options for the backend proxy:

### Option A: Flask (currently active)
- `app.py` — thin Flask proxy. Fetches XML from Eventor API, caches results in `cache.db` (SQLite, 30-min TTL, invalidated on date change). Routes: `GET /` (serves the HTML), `GET /my-events`, `GET /startlist?eventId=`.
- `start.sh` / `ecosystem.config.js` — PM2 runs gunicorn via the shell wrapper on the server.
- Nginx config in `nginx/eventor.fjoven.com` proxies port 80 → 127.0.0.1:5001.

### Option B: Cloudflare Worker (alternative)
- `cloudflare/worker.js` — same two routes as Flask, deployed with `wrangler deploy` from the `cloudflare/` directory.
- Secrets are set via `wrangler secret put EVENTOR_API_KEY` etc.
- When using the Worker, set `const WORKER_URL = 'https://...'` in `index.html`.

### Frontend
- `cloudflare/index.html` — single-file app, no build step. All logic is inline JS + CSS.
- Fetches XML from the backend, parses it with `DOMParser`, renders a filterable/sortable table.
- Uses `localStorage` to remember the last selected event across page refreshes.

## Key frontend conventions

- All colors are CSS custom properties defined in `:root` at the top of `index.html`.
- XML parsing uses namespace-agnostic helpers (`child`, `children`, `walkAll`, `txt`) — never use `querySelector` or `getElementsByTagName` with namespace prefixes on Eventor XML.
- `TRACKED` (full names) and `TRACKED_DISPLAY` (short display names) must stay in sync with `EVENTOR_TRACKED_IDS` in `.env` / `worker.js`.
- `OPPSAL_CLASSES` defines which classes are shown in the "Oppsal råtasser" summary card.
- Table sort state lives in `tableSort = { col, dir }`. Filter state lives in `tableFilter = { classes: Set, club, name }`.
- `parseStartList` returns competitors already sorted by class (`compareClasses`) then start time. Cards that display subsets of competitors do not need to re-sort.
