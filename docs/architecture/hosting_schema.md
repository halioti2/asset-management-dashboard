# Hosting Schema: Asset Management Dashboard on Fly.io

**Date:** 2026-03-09
**Status:** Pre-deployment plan
**Stack:** React (Vite) + Flask (Gunicorn) + SQLite + APScheduler + Google Sheets API

---

## Overview

In production, the React frontend is compiled into static files (`npm run build`) and served directly by Flask. There is a **single server process** (Gunicorn, 1 worker) running on Fly.io that handles both the HTML/JS/CSS page delivery and all `/api` calls. The persistent SQLite database lives on a Fly Volume mounted at `/data` and survives deploys. A background APScheduler thread polls Google Sheets every 3 minutes.

```
Local dev:
  Browser → Vite dev server (:5173) → [proxy /api] → Flask (:5001)

Production (Fly.io):
  Browser → Fly Edge (TLS :443) → Flask/Gunicorn (:8080)
                                        ├── serves index.html + JS/CSS (static)
                                        ├── handles /api/* routes
                                        ├── reads/writes /data/assets.db (Fly Volume)
                                        └── background thread → Google Sheets API
```

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  Internet                                                        │
│    │                                                             │
│    ▼                                                             │
│  Fly.io Edge (TLS termination, anycast, port 443 → 8080)        │
│    │                                                             │
│    ▼                                                             │
│  ┌───────────────────────────────────────────────┐              │
│  │  Fly Machine  (single, --ha=false)             │              │
│  │                                               │              │
│  │  /app/  (ephemeral container image)           │              │
│  │    ├── app.py          Flask app factory      │              │
│  │    ├── models.py       SQLite ORM             │              │
│  │    ├── routes/         API blueprints         │              │
│  │    ├── sync/           Sheets + poller        │              │
│  │    └── frontend/dist/  Built React app        │              │
│  │                                               │              │
│  │  /data/  (Fly Volume — persists across        │              │
│  │    ├── assets.db       deploys)               │              │
│  │    └── last_poll_cache.json                   │              │
│  └───────────────────────────────────────────────┘              │
│                         │                                        │
│                         │ outbound HTTPS                         │
│                         ▼                                        │
│                  Google Sheets API                               │
│            (service account credentials                          │
│             stored in fly secrets)                               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Sequence Diagram: Request Flows & Background Sync

```
Browser              Fly Edge (TLS)      Flask/Gunicorn       SQLite (/data)    Google Sheets API
   |                       |                    |                    |                   |
   |  ── PAGE LOAD ─────────────────────────────────────────────────────────────────────|
   |                       |                    |                    |                   |
   |-- GET / (HTTPS) ----->|                    |                    |                   |
   |                       |-- GET / ---------->|                    |                   |
   |                       |                    |-- serve index.html |                   |
   |<------------------------------ index.html + JS/CSS bundle ------|                   |
   |                       |                    |                    |                   |
   |-- GET /api/assets --->|                    |                    |                   |
   |                       |-- GET /api/assets->|                    |                   |
   |                       |                    |-- SELECT assets -->|                   |
   |                       |                    |<-- rows -----------|                   |
   |<------------------------------ 200 JSON asset list -------------|                   |
   |                       |                    |                    |                   |
   |  ── J1: CHECK OUT ──────────────────────────────────────────────────────────────── |
   |                       |                    |                    |                   |
   |-- PATCH /api/assets/:id/checkout -------->|                    |                   |
   |                       |-- PATCH ---------->|                    |                   |
   |                       |                    |-- UPDATE checkout->|                   |
   |                       |                    |<-- updated row ----|                   |
   |<------------------------------ 200 JSON (immediate) -----------|                   |
   |                       |                    |-- write_row() [async] ---------------->|
   |                       |                    |                    |                   |
   |  ── J2: RETURN ─────────────────────────────────────────────────────────────────── |
   |                       |                    |                    |                   |
   |-- PATCH /api/assets/:id/return ---------->|                    |                   |
   |                       |-- PATCH ---------->|                    |                   |
   |                       |                    |-- UPDATE returned->|                   |
   |                       |                    |-- INSERT new row ->|                   |
   |                       |                    |<-- both rows ------|                   |
   |<------------------------------ 200 JSON (immediate) -----------|                   |
   |                       |                    |-- write_row() existing row [async] --->|
   |                       |                    |-- append_row() new row [async] ------->|
   |                       |                    |                    |                   |
   |  ── J3: ADD LAPTOP ─────────────────────────────────────────────────────────────── |
   |                       |                    |                    |                   |
   |-- POST /api/assets -->|                    |                    |                   |
   |                       |-- POST ----------->|                    |                   |
   |                       |                    |-- INSERT asset --->|                   |
   |                       |                    |<-- new row --------|                   |
   |<------------------------------ 201 JSON -------------------|                        |
   |                       |                    |-- append_row() [async] --------------->|
   |                       |                    |                    |                   |
   |  ── J4/J5: LOCK / BULK NOTES ───────────────────────────────────────────────────── |
   |                       |                    |                    |                   |
   |-- PATCH /api/assets/:id/lock (or /notes)->|                    |                   |
   |                       |-- PATCH ---------->|                    |                   |
   |                       |                    |-- UPDATE notes --->|                   |
   |                       |                    |<-- updated row ----|                   |
   |<------------------------------ 200 JSON (immediate) -----------|                   |
   |                       |                    |-- write_row() [async] ---------------->|
   |                       |                    |                    |                   |
   |  ── BACKGROUND POLLER (APScheduler, every 3 min) ───────────────────────────────── |
   |                       |                    |                    |                   |
   |                       |                    |-- read_all_rows() ------------------- >|
   |                       |                    |<--------------------------------------------- all rows
   |                       |                    |-- load cache ----->|                   |
   |                       |                    |<-- cached state ---|                   |
   |                       |                    |                    |                   |
   |                       |              [for each row, compare sheets vs cache vs db] |
   |                       |                    |                    |                   |
   |                       |         Sheets changed, DB unchanged:   |                   |
   |                       |                    |-- upsert to db --->|                   |
   |                       |                    |                    |                   |
   |                       |         DB changed, Sheets unchanged:   |                   |
   |                       |                    |-- write_row() retry ------------------>|
   |                       |                    |                    |                   |
   |                       |         Both changed (CONFLICT — Sheets wins):             |
   |                       |                    |-- upsert to db --->|                   |
   |                       |                    |                    |                   |
   |                       |                    |-- save cache ----->|                   |
   |                       |                    |                    |                   |
   |  ── STARTUP SEQUENCE (first boot only — skipped when DB already has data) ────────|
   |                       |                    |                    |                   |
   |                       |          [Fly Volume /data mounted]     |                   |
   |                       |                    |-- init_db() ------>|                   |
   |                       |                    |-- ensure_schema() ------------------- >|
   |                       |                    |<--------------------------------------------- headers confirmed
   |                       |                    |-- read_all_rows() ------------------- >|
   |                       |                    |<--------------------------------------------- all rows (seed)
   |                       |                    |-- upsert rows ---->|                   |
   |                       |                    |-- APScheduler.start() (3-min loop)    |
   |                       |                    |                    |                   |
```

---

## Function Call Chain

### User action → Database → Google Sheets

```
Browser click (e.g. "Check Out")
  └── CheckOutForm.jsx  onSubmit()
        └── api/assets.js  checkoutAsset(id, data)
              └── axios.patch('/api/assets/:id/checkout')
                    └── routes/assets.py  checkout_asset(asset_id)
                          ├── models.py  get_asset_by_id()        → SQLite read
                          ├── models.py  derive_status()          → validation
                          ├── models.py  update_asset(id, fields) → SQLite write
                          └── sync/sheets.py  write_row(asset)    → Sheets API (async)
                    ← 200 JSON
              ← resolved promise
        └── onSuccess() → App.jsx fetchAssets() → GET /api/assets → re-render table
```

### Background sync cycle (every 3 min)

```
APScheduler trigger (BackgroundScheduler thread)
  └── app.py  _poll_job()
        └── sync/poller.py  run_poll()
              ├── _load_cache()            → reads /data/last_poll_cache.json
              ├── sync/sheets.py  read_all_rows()   → Sheets API
              ├── for each row:
              │     ├── models.py  get_asset_by_sheets_row()   → SQLite
              │     ├── conflict resolution logic
              │     ├── models.py  upsert_asset_from_sheets()  → SQLite (if needed)
              │     └── sync/sheets.py  write_row()            → Sheets (if needed)
              └── _save_cache()            → writes /data/last_poll_cache.json
```

### Startup sequence (container boot)

```
Fly Machine starts → /data volume mounted
  └── gunicorn  "app:create_app()"
        └── app.py  create_app()
              ├── Flask()             — static_folder='frontend/dist'
              ├── init_db()           — CREATE TABLE IF NOT EXISTS (models.py)
              ├── register_blueprint(assets_bp)
              ├── ensure_schema()     — adds Email/Phone/Last Updated to Sheets if missing
              ├── _initial_sync()     — if DB empty: pull all Sheets rows → SQLite
              └── APScheduler.start() — every 3 min background poll
```

---

## What Changes from Local Dev to Production

| Concern | Local dev | Production (Fly.io) |
|---------|-----------|---------------------|
| Frontend serving | Vite dev server (:5173) proxies `/api` → Flask | Flask serves `frontend/dist/` directly |
| Backend port | Flask :5001 | Gunicorn :8080 |
| Database path | `./assets.db` (working dir) | `/data/assets.db` (Fly Volume, persistent) |
| Poll cache path | `/app/sync/last_poll_cache.json` (ephemeral) | `/data/last_poll_cache.json` (Fly Volume) |
| Google credentials | `.env` file (GOOGLE_SHEETS_CREDENTIALS) | `fly secrets set GOOGLE_SHEETS_CREDENTIALS` |
| Google Sheet ID | `.env` file (GOOGLE_SHEET_ID) | `fly secrets set GOOGLE_SHEET_ID` |
| FLASK_ENV | `development` | `production` |
| CORS | Required (different origins) | Not needed (same origin), but harmless |
| Reloader | Werkzeug reloader enabled | Gunicorn, no reloader |

---

## Deployment Plan: Code Changes Required

### 1. `backend/Dockerfile` — multi-stage build

Add a Node.js build stage before the Python stage to compile the React app. The built output (`frontend/dist/`) is copied into the Python image so Flask can serve it.

```dockerfile
# Stage 1: Build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=frontend-build /frontend/dist ./frontend/dist

ENV DATABASE_PATH=/data/assets.db
ENV FLASK_ENV=production
ENV PORT=8080

EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "app:create_app()"]
```

> **Note:** The Dockerfile context must be the **repo root** (not `backend/`), so it can access both `backend/` and `frontend/` in one build. The `fly.toml` `[build]` section must set `dockerfile = "Dockerfile"` (root-level).

### 2. `backend/app.py` — serve static files

Flask needs to know where the compiled frontend lives and serve `index.html` for any non-API route (so React Router / direct URL loads work).

```python
# Change Flask() constructor:
app = Flask(__name__, static_folder='frontend/dist', static_url_path='')

# Add catch-all route (before blueprint registration):
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    from flask import send_from_directory
    import os
    full_path = os.path.join(app.static_folder, path)
    if path and os.path.exists(full_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')
```

> The `/api` blueprint is registered with `url_prefix='/api'`, so all `/api/*` routes are handled by Flask before falling through to the catch-all.

### 3. `backend/sync/poller.py` — move cache to persistent volume

The poll cache is currently written next to the source file (`/app/sync/last_poll_cache.json`), which is in the ephemeral container layer and lost on every redeploy. It must live on the Fly Volume.

```python
# Change CACHE_PATH:
CACHE_PATH = os.path.join(os.getenv('DATA_DIR', '/data'), 'last_poll_cache.json')
```

### 4. `fly.toml` — create at repo root

```toml
app = "spreadsheets-assets"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[env]
  FLASK_ENV = "production"
  DATABASE_PATH = "/data/assets.db"
  DATA_DIR = "/data"
  PORT = "8080"

[[mounts]]
  source = "assets_data"
  destination = "/data"
  initial_size = "1gb"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[[http_service.checks]]
  grace_period = "15s"
  interval = "30s"
  timeout = "5s"
  method = "GET"
  path = "/api/assets"

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
```

### 5. First-time deploy commands

```bash
# 1. Authenticate
fly auth login

# 2. Create the app (--ha=false = single machine, no HA — required for SQLite)
fly launch --ha=false --no-deploy

# 3. Create the persistent volume (ONCE, in your target region)
fly volumes create assets_data --size 1 --region iad

# 4. Set secrets (env var names must match what sheets.py and models.py read)
fly secrets set GOOGLE_SHEETS_CREDENTIALS="$(cat path/to/service-account.json)"
fly secrets set GOOGLE_SHEET_ID="your-sheet-id-here"

# 5. Deploy
fly deploy

# 6. Verify
fly logs
fly status
```

---

## Known Constraints (summary from research)

| Constraint | Reason | Mitigation |
|------------|--------|------------|
| Single machine only | SQLite can't be shared across machines | `fly launch --ha=false`, never `fly scale count 2` |
| Volume must exist before first deploy | Mount fails silently → ephemeral DB | `fly volumes create` before `fly deploy` |
| `release_command` has no volume access | Fly architectural constraint | DB init in `create_app()`, not release_command |
| Gunicorn workers must stay at 1 | N workers = N APScheduler threads = duplicate polls | `--workers 1` pinned in Dockerfile CMD |
| Cache must be on `/data` | Container layer is wiped on redeploy | `DATA_DIR=/data` env var, path in poller.py |
| Google credentials not in image | Security | `fly secrets set` only |
