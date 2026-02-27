# Product Requirements Document: Asset Management Dashboard

**Version:** 1.0 MVP
**Date:** 2026-02-26
**Status:** Approved for Implementation

---

## Overview

A single-user admin dashboard for managing laptop/equipment checkout and return. The system uses a React frontend, Flask backend with SQLite database, and bidirectional sync with Google Sheets (Distribution Tracker) as a secondary source of truth.

---

## Goals

- Replace manual Google Sheets data entry with a structured admin interface
- Track equipment checkout/return lifecycle with contact info
- Maintain Google Sheets as a human-readable audit log
- Provide fast, consistent data via local SQLite database

---

## Non-Goals (MVP)

- Multi-user support / authentication
- Real-time updates (< 3 min sync acceptable)
- Mobile responsive design
- MDM Wipe functionality (button is visual placeholder only)
- Offline support

---

## UI Layout

Single-page 3-section layout:

```
┌─────────────────────────────────────────────┐
│  [Check Out] [Return] [Add Laptop]           │  <- Action Buttons
│  [Lock] [Update Notes]                       │
├─────────────────────────────────────────────┤
│  Status ▼  Type ▼  Assigned To ▼            │  <- Filters & Search
│  Lease End Date: [after ▼] [before ▼]       │
├─────────────────────────────────────────────┤
│  ☐  Label  Type  Serial#  Status  Assigned  │  <- Data Table
│     To  Lease End  Notes  Returned          │
│  ☐  ...                                     │
│  ☐  ...                                     │
└─────────────────────────────────────────────┘
```

Clicking an action button opens a form panel in the top section above the table. Selecting a row auto-populates read-only fields in the form.

---

## Data Model

### SQLite / Google Sheets Columns

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| label | text | No | Equipment label (e.g. "MacBook Air #1") |
| type | text | Yes | MacBook Air, MacBook Pro, Dell XPS, iPad, etc. |
| serial_number | text | Yes | Unique identifier |
| category | text | Yes | Purchased (Apple), Lease (Temp), etc. |
| date_assigned | date | Yes | When added to inventory |
| lease_end_date | date | No | Apple lease expiry |
| assigned_to | text | No | Current borrower name |
| email | text | No | Borrower email |
| phone | text | No | Borrower phone |
| notes | text | No | Multi-purpose: condition, setup, lock reason, misc |
| returned | date | No | When returned (empty = active checkout) |
| last_updated | datetime | System | Auto-updated on every write, not displayed |

### Derived Status (not stored)

| Status | Condition |
|--------|-----------|
| Checked Out | Category = "Lease Temp" AND returned empty AND assigned_to set AND assigned_to ≠ "ready to assign" |
| Historical | Category = "Lease Temp" AND assigned_to set AND assigned_to ≠ "ready to assign" AND returned filled |
| Not Assigned | returned empty AND (assigned_to empty OR assigned_to = "ready to assign") |
| Locked | notes contains lock reason |

---

## User Journeys

### J1: Check Out
Admin assigns a laptop to a student.

**Trigger:** Click [Check Out]
**Requires:** Select one laptop from table

**Form inputs:**
- Assigned To (text, required)
- Email (email, required)
- Phone (tel, required)
- Duration Needed (dropdown: "1 day" | "1 semester", UI only)

**Auto-populated (read-only):**
- Serial # (from selected row)
- Type (from selected row)
- Lease End Date (from selected row, Apple lease date)

**On submit:**
- Writes: assigned_to, email, phone, last_updated
- Status derives to: "Checked Out"
- Validation: all required fields filled, laptop must be Not Assigned

---

### J2: Return
Admin processes a returned laptop and notes condition.

**Trigger:** Click [Return]
**Requires:** Select one laptop from table

**Form inputs:**
- Notes (textarea — condition: Excellent / Good / Fair / Damaged, required)
- [MDM Wipe] button (non-functional placeholder)

**Auto-populated (read-only):**
- Serial # (from selected row)
- Type (from selected row)
- Assigned To (from selected row)

**On submit:**
- Writes: notes (appended), returned = today, last_updated
- Status derives to: "Historical"
- Validation: laptop must be Checked Out

---

### J3: Add Laptop
Admin adds new equipment to inventory.

**Trigger:** Click [Add Laptop]
**Requires:** No row selection

**Form inputs:**
- Label (text, optional)
- Type (dropdown, required)
- Serial # (text, required)
- Category (dropdown, required)
- Date Assigned (date picker, required)
- Lease End Date (date picker, optional)
- Notes (textarea, optional — setup notes)

**On submit:**
- Creates new record
- Validation: serial_number must be unique

---

### J4: Lock
Admin marks a laptop as locked/compromised.

**Trigger:** Click [Lock]
**Requires:** Select one laptop from table

**Form inputs:**
- Notes (textarea — lock reason, optional)

**Auto-populated (read-only):**
- Serial # (from selected row)
- Type (from selected row)

**On submit:**
- Writes: notes (appended with lock reason + timestamp), last_updated
- Status derives to: "Locked"
- Row highlighted in table

---

### J5: Update Notes
Admin edits or appends notes on one or more records.

**Trigger:** Click [Update Notes]
**Requires:** Select one or more laptops from table (checkboxes)

**Form inputs:**
- Notes (textarea — editable content)

**On submit:**
- Writes: notes (replaces), last_updated for all selected records
- Validation: at least one record selected

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/assets | List all assets with filters |
| POST | /api/assets | Create new asset (J3) |
| PATCH | /api/assets/:id/checkout | Check out asset (J1) |
| PATCH | /api/assets/:id/return | Return asset (J2) |
| PATCH | /api/assets/:id/lock | Lock asset (J4) |
| PATCH | /api/assets/notes | Bulk update notes (J5) |

### GET /api/assets query params
- `status`: checked_out | not_assigned | historical | locked
- `assigned_to`: string
- `type`: string
- `lease_end_date_before`: ISO date
- `lease_end_date_after`: ISO date

---

## Sync Architecture

### Flow
```
React → PATCH /api/assets/:id/checkout
      → Flask writes SQLite immediately
      → Flask queues Sheets API write
      → Returns 200 to React

Background thread (every 3 min):
  → Poll Google Sheets
  → For each row:
    - Poll unchanged + DB differs  → frontend wins, retry Sheets write
    - Poll changed + DB unchanged  → external change, merge to SQLite
    - Poll changed + DB differs    → CONFLICT, Sheets wins, log it
```

### Initial Sync
On first startup, poll Google Sheets and populate SQLite. Sheets is source of truth on boot.

---

## File Structure

```
Spreadsheets/
├── backend/
│   ├── app.py                  # Flask app entry point
│   ├── models.py               # SQLite schema + helpers
│   ├── routes/
│   │   └── assets.py           # API route handlers
│   ├── sync/
│   │   ├── sheets.py           # Google Sheets read/write
│   │   └── poller.py           # Background polling + conflict logic
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ActionBar.jsx   # 5 action buttons
│   │   │   ├── FilterBar.jsx   # Filters + search
│   │   │   ├── AssetTable.jsx  # Data table with checkboxes
│   │   │   └── forms/
│   │   │       ├── CheckOutForm.jsx
│   │   │       ├── ReturnForm.jsx
│   │   │       ├── AddLaptopForm.jsx
│   │   │       ├── LockForm.jsx
│   │   │       └── UpdateNotesForm.jsx
│   │   └── api/
│   │       └── assets.js       # API calls
│   ├── package.json
│   └── vite.config.js
├── .env
├── venv/
└── docs/
```

---

## Implementation Order

1. Flask backend scaffold + SQLite init
2. Initial Sheets → SQLite sync on startup
3. GET /api/assets with filtering + derived status
4. POST /api/assets (Add Laptop)
5. PATCH endpoints (Check Out, Return, Lock, Bulk Notes)
6. Background poller + conflict resolution
7. React scaffold (Vite + Tailwind)
8. AssetTable component
9. FilterBar component
10. ActionBar + all 5 forms
11. Fly.io deployment config
