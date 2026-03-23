# Research: Gunicorn Fork/Thread Deadlock with APScheduler

**Date:** 2026-03-23
**Author:** Ethan Davey, Claude Code

---

## Executive Summary

Every `fly deploy` left the app in a deadlocked state with health checks failing. Root cause: `BackgroundScheduler` was started in `create_app()`, which gunicorn's factory pattern calls in the **master process** before forking workers. Background threads do not survive `fork()` — but the locks they hold do. Workers inherited locked mutexes with no thread to release them, causing every worker to deadlock on startup. Fix: move scheduler start to a `gunicorn.conf.py` `post_fork` hook so it runs only in the worker process, after forking.

---

## Sequence Diagram

**Broken (before fix)**
```
gunicorn master
  └─ calls create_app()
       └─ BackgroundScheduler starts → background thread T begins Sheets API call
            └─ T acquires lock L
  └─ forks worker
       └─ worker inherits: app object, lock L (locked), no thread T
            └─ worker tries to acquire L → deadlock
            └─ gunicorn accepts HTTP connections but worker never responds → health check fails
```

**Fixed (after fix)**
```
gunicorn master
  └─ calls create_app()
       └─ scheduler NOT started
  └─ forks worker
       └─ post_fork hook fires in worker
            └─ BackgroundScheduler starts cleanly in worker process
            └─ worker ready → health check passes
```

---

## Architecture Diagram

```
Dockerfile CMD
  └─ gunicorn --config gunicorn.conf.py app:create_app()
       │
       ├─ master process
       │    └─ create_app() → Flask app (no scheduler)
       │
       └─ worker process (post_fork)
            └─ start_scheduler() → BackgroundScheduler
                 └─ _startup_job() every 3 min
                      ├─ if DB empty → force_sync_from_sheets()
                      └─ else → run_poll()
```

---

## Problem vs Solution

| | Before | After |
|---|---|---|
| Scheduler start location | `create_app()` — master process | `gunicorn.conf.py post_fork` — worker process |
| Thread survives fork | No — deadlock | N/A — thread starts after fork |
| `fly deploy` result | Health check fails every time | Health check passes on first deploy |
| Manual recovery needed | SSH seed + machine restart | None |
| Dev mode | Scheduler in `create_app()` (safe, no fork) | Same — dev branch still starts inline |

---

## Side-by-Side Comparison

**Before — app.py**
```python
def create_app():
    app = Flask(__name__)
    # ...
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=_startup_job, ...)
    scheduler.start()  # ← starts thread in master
    return app
```

**After — app.py + gunicorn.conf.py**
```python
# app.py
def create_app():
    app = Flask(__name__)
    # ...
    if os.getenv('FLASK_ENV') == 'development':
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            start_scheduler()  # safe in dev — no fork
    return app

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=_startup_job, ...)
    scheduler.start()

# gunicorn.conf.py
def post_fork(server, worker):
    from app import start_scheduler
    start_scheduler()  # ← runs in worker, after fork
```

---

## Data Flow Diagram

```
fly deploy
  │
  ├─ [OLD] create_app() in master → scheduler thread starts → fork → deadlock → ✗
  │
  └─ [NEW] create_app() in master (no scheduler)
            └─ fork
                 └─ post_fork in worker
                      └─ start_scheduler()
                           └─ DB empty? → force_sync_from_sheets() → poll every 3 min → ✓
```
