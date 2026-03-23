# Thread-Safe Google API Service Caching

**Status:** reviewing
**Date:** 2026-03-16
**Participants:** Ethan Davey, Claude Code

---

## Executive Summary

The app was OOM-crashing on Fly.io (512MB) after running for several hours. Root cause: `get_service()` in `sync/sheets.py` calls `googleapiclient.discovery.build()` on every invocation, creating a new HTTP client and connection pool each time. These objects are not fully garbage-collected, causing slow memory growth. Fix: cache one service object per thread using `threading.local()`, which is both memory-efficient and safe given two threads share the module (gunicorn request thread + APScheduler background thread).

---

## Problem

### Symptom
Fly.io OOM notification: `gunicorn killed in frontend-rough-cloud-3819`. Logs confirmed the app ran stably for hours before crashing — a slow leak, not a startup spike.

### Root Cause

```
# Every poll cycle, every sheets write — a brand new client:
def get_service():
    creds_dict = json.loads(os.getenv('GOOGLE_SHEETS_CREDENTIALS'))
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('sheets', 'v4', credentials=credentials)  # ← new HTTP client every time
```

`build()` is called:
- Once per poll cycle (in `read_all_rows()`) — every 3 minutes
- Once per user-triggered write (`write_row`, `append_row`)

Each call allocates a new `httplib2.Http` connection pool and a discovery resource object. These don't always get GC'd because the Google client libraries hold internal references.

The `file_cache is only supported with oauth2client<4.0.0` log line (visible on every poll) confirms the discovery document was also being re-fetched from Google's servers each time rather than served from cache.

### Why Not a Simple Global?

The google-api-python-client official docs explicitly state that `httplib2.Http` objects are **not thread-safe**. Two threads share this module:

- **Thread A**: gunicorn request thread (handles user-triggered `/api/sync`, checkout, return, lock)
- **Thread B**: APScheduler `BackgroundScheduler` thread (polls every 3 minutes)

A single shared service object risks concurrent use of the same `httplib2.Http` instance → race condition on socket reads/writes.

---

## Decision

Cache one service object **per thread** using `threading.local()`. Each thread gets its own `httplib2` instance on first use, then reuses it for all subsequent calls on that thread. No lock needed — `threading.local` isolates by thread automatically.

```python
_thread_local = threading.local()

def get_service():
    if not hasattr(_thread_local, 'service'):
        creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        _thread_local.service = build('sheets', 'v4', credentials=credentials, cache_discovery=False)
    return _thread_local.service
```

`cache_discovery=False` suppresses the `file_cache` warning and skips the discovery document network round-trip entirely (the schema is stable; we don't need to re-fetch it).

---

## Swim Lane: Before vs After

### Before — new client every call

```
Request Thread          APScheduler Thread       Google API
     |                        |                      |
     |-- get_service() ------>|                      |
     |   build() called       |                      |
     |------------------------|----> fetch discovery->|
     |<-----------------------|<---- 50KB JSON -------|
     |   [Http client #1]     |                      |
     |                        |-- get_service()       |
     |                        |   build() called      |
     |                        |----> fetch discovery->|
     |                        |<---- 50KB JSON -------|
     |                        |   [Http client #2]    |
     |                        |                      |
     |-- get_service() ------>|                      |
     |   build() called       |                      |
     |   [Http client #3]     |                      |   ← #1 and #2 not GC'd yet
     |                        |                      |
     ...accumulates over hours...
     |                        |                      |
     OOM                      |                      |
```

### After — one client per thread, reused

```
Request Thread          APScheduler Thread       Google API
     |                        |                      |
     |-- get_service() ------>|                      |
     |   thread_local miss    |                      |
     |   build() called once  |                      |
     |------------------------|----> fetch discovery->|  ← only on first call
     |<-----------------------|<---- 50KB JSON -------|
     |   [Http client A]      |                      |
     |   stored in local.A    |                      |
     |                        |-- get_service()       |
     |                        |   thread_local miss   |
     |                        |   build() called once |
     |                        |----> fetch discovery->|  ← only on first call
     |                        |<---- 50KB JSON -------|
     |                        |   [Http client B]     |
     |                        |   stored in local.B   |
     |                        |                      |
     |-- get_service() ------>|                      |
     |   thread_local hit     |                      |
     |   return client A      |                      |  ← no allocation, no network
     |                        |-- get_service()       |
     |                        |   thread_local hit    |
     |                        |   return client B     |  ← no allocation, no network
     |                        |                      |
     memory stable ✓          |                      |
```

---

## Memory Impact Diagram

```
RAM (MB)
512 |                                          ██ OOM
    |                                     ████
    |                               ██████
    |                         ██████
    |                   ██████
    |             ██████
    |       ██████
320 | ██████   ← baseline ~220MB + gradual leak
    |
    | [Before fix — slow growth to OOM over hours]
    |
    |_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
    |
320 | ██████████████████████████████████████████
    |   ← baseline ~220MB, stable, no growth
    |
    | [After fix — flat line]
    |
    +-------------------------------------------> time
```

---

## Interaction With Existing Architecture

### APScheduler single-worker constraint (ADR 001)
`auto_stop_machines = 'off'` and `min_machines_running = 1` in `fly.toml` ensure exactly one machine runs. APScheduler's `BackgroundScheduler` spawns one background thread inside the single gunicorn worker. This remains safe — `threading.local` gives each thread its own service object with zero coordination overhead.

**Risk if scaling to multiple workers:** APScheduler would run in each worker, each polling Sheets independently and writing back conflicts. This is a pre-existing constraint from ADR 001, not introduced by this change.

### SQLite WAL mode
Unrelated to this change. Note: the git history shows WAL files were manually removed once (`e1149fe`), indicating a prior crash left the DB in a dirty state. WAL + Fly.io volumes is functional but fragile — if the machine crashes mid-write, the `.wal` file can be left behind and corrupt the DB on next startup. Not in scope for this ADR but worth tracking.

---

## Alternatives Considered

| Option | Pros | Cons | Decision |
|---|---|---|---|
| Simple global `_service = None` | Simplest code | Not thread-safe per official docs | Rejected |
| `threading.local` per-thread cache | Thread-safe, minimal allocations, standard pattern | Two service objects exist (one per thread) — negligible RAM | **Chosen** |
| Pass `Http()` instance per call | Thread-safe | Creates new Http per call — same leak in different form | Rejected |
| Bump RAM to 1024MB | Zero code change | Treats symptom not cause, costs ~$5/mo, will still leak | Rejected as primary fix |
| Reduce poll frequency | Less pressure | Doesn't fix leak, just slows it | Rejected |

---

## Files Changed

- `backend/sync/sheets.py` — replace `get_service()` with thread-local cached version

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Stale credentials after token expiry | Low | `google-auth` service account credentials auto-refresh; the cached `Credentials` object handles this internally |
| Broken HTTP connection not recovered | Low | `httplib2` reconnects on next request automatically |
| Future scale to multiple gunicorn workers | Medium (if needed) | APScheduler must move to a separate process or use `--preload` before adding workers |
