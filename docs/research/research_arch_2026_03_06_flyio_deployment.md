# Research: Fly.io Deployment — Flask + SQLite + Google Sheets Sync

**Date:** 2026-03-06
**Status:** Draft
**Scope:** Fly.io quickstart for our stack (Flask, Gunicorn, SQLite on persistent volume, APScheduler background poller)

---

## Executive Summary

### Non-Technical Summary

Fly.io is the hosting service we're using to put this app on the internet. Think of it like renting a small computer in the cloud that runs our app 24/7. The main thing to be aware of is that our database (the file that stores all the asset records) needs to live on a dedicated storage drive we attach to that computer — otherwise every time we update the app, the database gets wiped. We also need to make sure only one copy of the app is running at a time, since our database can't be shared across multiple copies simultaneously. Setup requires a few manual steps the first time (creating that storage drive, loading in our Google credentials), but after that, deploying updates is a single command.

### Technical Summary

Fly.io is a viable deployment target for this app. The key constraint is SQLite: Fly defaults to two machines (HA mode), which breaks a single-file SQLite database. We must deploy with `--ha=false` (single machine). The persistent volume at `/data` must exist before first deploy, and the `DATABASE_PATH` env var must point to it. The `release_command` in `fly.toml` does NOT have volume access — any DB init must happen at container startup, not as a release command. Our `Dockerfile` already covers build; we need a `fly.toml` in the repo root (or `backend/`) and a volume created via `flyctl` before first deploy.

---

## Sequence Diagram

```
Developer                  flyctl CLI              Fly.io Platform         Container
    |                          |                        |                      |
    |-- fly launch ----------->|                        |                      |
    |                          |-- detect Dockerfile -->|                      |
    |                          |-- create app --------->|                      |
    |                          |-- write fly.toml ----->|                      |
    |                          |                        |                      |
    |-- fly volumes create --->|                        |                      |
    |                          |-- provision volume ---->|                      |
    |                          |                        |                      |
    |-- fly secrets set ------>|                        |                      |
    |                          |-- store secrets ------->|                      |
    |                          |                        |                      |
    |-- fly deploy ----------->|                        |                      |
    |                          |-- build image -------->|                      |
    |                          |-- run release_cmd ---->| (NO volume access)   |
    |                          |-- start machine ------>|                      |
    |                          |                        |-- mount /data ------->|
    |                          |                        |-- run CMD (gunicorn)->|
    |                          |                        |                      |-- init DB if needed
    |                          |                        |                      |-- start APScheduler
    |                          |                        |                      |-- serve requests
```

---

## Architecture Diagram

```
Internet
   |
   v
Fly.io Edge (TLS termination, port 443 -> 8080)
   |
   v
Fly Machine (single, --ha=false)
   |
   +-- /app/          (container image, ephemeral)
   |    +-- backend/  (Flask + Gunicorn + APScheduler)
   |
   +-- /data/         (Fly Volume, persistent across deploys)
        +-- assets.db (SQLite database)

External:
   Fly Machine <---> Google Sheets API (outbound HTTPS)
   Fly Machine <---> Google Service Account credentials (via fly secrets)
```

---

## Data Flow Diagram

```
fly deploy triggered
       |
       v
  Build Docker image (backend/Dockerfile)
       |
       v
  release_command runs? --> NO volume access here, skip DB init
       |
       v
  Machine starts, /data volume mounted
       |
       v
  gunicorn starts -> app.py create_app()
       |
       v
  startup sync: Sheets -> SQLite (all rows)
       |
       v
  APScheduler starts background poller (every 3 min)
       |
       v
  App ready, health check passes
       |
       v
  Fly proxy routes traffic to port 8080
```

---

## Problem vs Solution

| Problem | Solution |
|---------|----------|
| Fly defaults to 2 machines (HA), breaks SQLite single-file | `fly launch --ha=false` + `fly scale count 1` |
| SQLite lives in ephemeral container layer, lost on redeploy | Mount Fly Volume at `/data`, set `DATABASE_PATH=/data/assets.db` |
| `release_command` runs before volume is mounted | Do NOT use `release_command` for DB init; handle in app startup (`create_app()`) |
| Google service account credentials can't be in image | `fly secrets set GOOGLE_CREDENTIALS_JSON='...'` |
| Volume must exist before first deploy | Run `fly volumes create` manually before `fly deploy` |
| APScheduler spawns threads; gunicorn workers > 1 would run N pollers | Already pinned to `--workers 1` in Dockerfile CMD |
| React frontend is separate (Vite) — not served by Flask | Serve built frontend as Flask static files, or deploy separately |

---

## Real-World Examples

- [fly-apps/hello-gunicorn-flask](https://github.com/fly-apps/hello-gunicorn-flask) — Official Fly Flask + Gunicorn example with `fly.toml` and Dockerfile
- [Using SQLite for Django on Fly.io](https://programmingmylife.com/2023-11-06-using-sqlite-for-a-django-application-on-flyio.html) — Detailed walkthrough of persistent volume + SQLite path config; startup script pattern
- [Fly.io community: SQLite not permanent storage](https://community.fly.io/t/your-username-and-password-didnt-match-please-try-again-sqlite-not-permanent-storage/22260) — Common failure mode when volume is not mounted

---

## Side-by-Side Comparison: Key fly.toml Sections

### Minimal working fly.toml for our stack

```toml
app = "spreadsheets-assets"
primary_region = "iad"

[build]
  dockerfile = "backend/Dockerfile"

[env]
  FLASK_ENV = "production"
  DATABASE_PATH = "/data/assets.db"
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

[deploy]
  strategy = "rolling"
  # Do NOT use release_command — volume not mounted at release time

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
```

### What NOT to do

```toml
# WRONG: release_command has no volume access — DB init will fail
[deploy]
  release_command = "python init_db.py"

# WRONG: multiple workers will each spawn an APScheduler poller
# CMD ["gunicorn", "--workers", "4", ...]
```

---

## Quickstart Steps (our app)

```bash
# 1. Install flyctl and authenticate
brew install flyctl
fly auth login

# 2. From repo root, launch (generates fly.toml — we'll overwrite it)
fly launch --ha=false --no-deploy

# 3. Create the persistent volume (do this ONCE, in your target region)
fly volumes create assets_data --size 1 --region iad

# 4. Set secrets (never commit these)
fly secrets set GOOGLE_CREDENTIALS_JSON="$(cat path/to/service-account.json)"

# 5. Deploy
fly deploy

# 6. Verify
fly logs
fly status
```

---

## Known Issues & Gotchas

### 1. Volume must be created before first deploy
If you `fly deploy` before `fly volumes create`, the mount fails silently and `/data` is ephemeral — SQLite writes are lost on restart.

### 2. `release_command` cannot access volumes
This is a Fly.io architectural constraint. The release VM is a separate, ephemeral machine without volume access. Any DB initialization must happen inside `create_app()` or a startup entrypoint script.

### 3. Single machine required
Running `fly scale count 2` (or forgetting `--ha=false`) with SQLite will cause one machine to own the write lock and the other to fail. Stick to 1 machine.

### 4. APScheduler + Gunicorn workers
Our Dockerfile already sets `--workers 1`. If this ever changes, the APScheduler background thread will run N times (once per worker), causing duplicate Sheets writes and poll conflicts. This must stay at 1 worker.

### 5. Auto-stop machines
Fly can auto-stop idle machines (`auto_stop_machines = true`). When the machine restarts, the startup sync runs again (Sheets → SQLite), which is correct per our PRD. Cold start adds ~2-5s latency on first request.

### 6. Frontend deployment
The React frontend (Vite build output) is not currently served by Flask. The recommended approach is to build the frontend into static files (`npm run build`) and serve them directly from Flask on the same port as the API — no second server or separate deployment needed.

This works because Vite compiles the React app into plain HTML/CSS/JS that the browser runs entirely client-side. All filtering, re-renders, and state changes happen in the browser after the initial page load — Flask has no involvement. The only server communication is the `/api` calls, which already use a relative base URL (`baseURL: '/api'`) and will hit Flask directly with no changes needed.

The difference from localhost: locally, Vite's dev server runs on port 5173 and proxies `/api` calls to Flask on port 5001. In production there is only one server (Flask on 8080), so the proxy is unnecessary and the setup is actually simpler.

**What needs to change:**
  - `Dockerfile`: add a build stage that runs `npm run build` and copies `frontend/dist/` into the image
  - `app.py`: configure Flask to serve `index.html` for any non-`/api` route (`static_folder` + catch-all route)

This is not a blocker — it is a known, straightforward build step.

### 7. Google Sheets credentials
The service account JSON must be available at runtime. Set via `fly secrets set` — it will be available as an environment variable. Our `sheets.py` must read from env rather than a local file path when `FLASK_ENV=production`.

---

## Sources

- [Run a Flask App — Fly Docs](https://fly.io/docs/python/frameworks/flask/)
- [App configuration (fly.toml) — Fly Docs](https://fly.io/docs/reference/configuration/)
- [Using SQLite for a Django application on fly.io](https://programmingmylife.com/2023-11-06-using-sqlite-for-a-django-application-on-flyio.html)
- [fly-apps/hello-gunicorn-flask — GitHub](https://github.com/fly-apps/hello-gunicorn-flask)
- [SQLite not permanent storage — Fly.io Community](https://community.fly.io/t/your-username-and-password-didnt-match-please-try-again-sqlite-not-permanent-storage/22260)
- [Deploying Python/Flask + DB — Fly.io Community](https://community.fly.io/t/deploying-python-flask-db/8456)
- [Can't create SQLite DB in mounted volume — Fly.io Community](https://community.fly.io/t/cant-create-sqlite-database-in-mounted-volume/2925)
