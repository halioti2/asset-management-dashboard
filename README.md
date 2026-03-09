# Asset Management Dashboard

A single-user admin dashboard for managing laptop/equipment checkout and return. React frontend, Flask backend, SQLite database, with bidirectional sync to a Google Sheets tracker.

**Live app:** https://frontend-rough-cloud-3819.fly.dev

---

## What it does

- **Check out** equipment to a student (name, email, phone)
- **Return** equipment and log condition notes
- **Lock** a device and log the reason
- **Add** new equipment to inventory
- **Bulk update notes** across multiple records
- **Syncs bidirectionally** with a Google Sheet every 3 minutes

---

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + Vite + Tailwind |
| Backend | Flask (Python 3.11) |
| Database | SQLite (persistent Fly Volume) |
| Sync | Google Sheets API (3-min polling) |
| Hosting | Fly.io |

---

## Project structure

```
Spreadsheets/
├── backend/
│   ├── app.py                  # Flask app factory + APScheduler
│   ├── models.py               # SQLite schema + query helpers
│   ├── routes/
│   │   └── assets.py           # API route handlers (5 journeys)
│   └── sync/
│       ├── sheets.py           # Google Sheets read/write
│       └── poller.py           # Background polling + conflict resolution
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── ActionBar.jsx
│           ├── FilterBar.jsx
│           ├── AssetTable.jsx
│           └── forms/          # CheckOut, Return, AddLaptop, Lock, UpdateNotes
├── docs/
│   ├── architecture/           # ADR + hosting schema
│   ├── planning/               # PRD + user journeys
│   └── research/               # Fly.io + Google Sheets sync research
├── Dockerfile                  # Multi-stage: Node build + Python runtime
├── fly.toml                    # Fly.io config
└── .env                        # Secrets (not committed)
```

---

## Local development

**Prerequisites:** Python 3.11+, Node 18+, a Google service account JSON credential.

### Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python app.py
# Runs on http://localhost:5001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173, proxies /api to :5001
```

### Environment variables (`.env` in repo root)

```
GOOGLE_CREDENTIALS=<service account JSON as single-line string>
SPREADSHEET_ID=<Google Sheet ID>
SHEET_NAME=<tab name, e.g. "Distribution Tracker">
DATABASE_PATH=backend/assets.db   # local path
DATA_DIR=backend/                 # local path for poll cache
```

---

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/assets` | List all assets (filterable) |
| POST | `/api/assets` | Add new asset |
| PATCH | `/api/assets/:id/checkout` | Check out asset |
| PATCH | `/api/assets/:id/return` | Return asset |
| PATCH | `/api/assets/:id/lock` | Lock asset |
| PATCH | `/api/assets/notes` | Bulk update notes |
| POST | `/api/assets/sync` | Force sync from Sheets (admin) |

**GET filters:** `status`, `assigned_to`, `type`, `lease_end_date_before`, `lease_end_date_after`

---

## Sync architecture

SQLite is the primary read/write store. Google Sheets is a human-readable audit log that stays in sync via a background poller.

```
App action → SQLite (immediate) → Sheets write (fire-and-forget) → cache updated

Background poller (every 3 min):
  sheets unchanged + db changed  → frontend wins, retry Sheets write
  sheets changed  + db unchanged → external change, merge to SQLite
  sheets changed  + db changed   → CONFLICT, Sheets wins, log it
```

On first boot with an empty DB, all rows are seeded from Sheets. On subsequent boots, the poller fires immediately to catch any Sheets changes made while the server was down.

---

## Deployment (Fly.io)

```bash
fly deploy --ha=false
```

Secrets required:
```bash
fly secrets set GOOGLE_CREDENTIALS='<service account JSON>'
fly secrets set SPREADSHEET_ID='<sheet id>'
fly secrets set SHEET_NAME='<tab name>'
```

SQLite and the poll cache live on a persistent Fly Volume mounted at `/data`.
