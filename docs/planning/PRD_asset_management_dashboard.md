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

### Original Google Sheets Columns (pre-app)

The Distribution Tracker sheet as it existed before app integration — no Email, Phone, or Last Updated columns.

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| Label | text | Yes | Equipment identifier (e.g. "MacBook Air #1") |
| Type | text | Yes | MacBook Air, MacBook Pro, Dell XPS, iPad, etc. |
| Serial # | text | Yes | Identifies the physical device; multiple rows per serial allowed (one per checkout event) |
| Category | text | Yes | Purchased (Apple), Lease (Temp), etc. |
| Date Assigned | date | Yes | When added to inventory |
| Lease End Date | date | No | Apple lease expiry |
| Assigned To | text | No | Current borrower name |
| Notes | text | No | Single free-text field: condition, setup, lock reason, misc |
| Returned | date | No | When returned (empty = active checkout) |

#### Original Derived Status (not stored)

| Status | Condition |
|--------|-----------|
| Checked Out | Category = "Lease (Temp)" AND Returned empty AND Assigned To set AND Assigned To ≠ "ready to assign" |
| Historical | Category = "Lease (Temp)" AND Assigned To set AND Assigned To ≠ "ready to assign" AND Returned filled |
| Not Assigned | Returned empty AND (Assigned To empty OR Assigned To = "ready to assign") |
| Locked | Notes contains lock reason |

---

### SQLite / Google Sheets Columns

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| label | text | No | Equipment label (e.g. "MacBook Air #1") |
| type | text | Yes | MacBook Air, MacBook Pro, Dell XPS, iPad, etc. |
| serial_number | text | Yes | Identifies the physical device; multiple records per serial allowed (one per checkout event) |
| category | text | Yes | Purchased (Apple), Lease (Temp), etc. |
| date_assigned | date | Yes | When added to inventory |
| lease_end_date | date | No | Apple lease expiry |
| assigned_to | text | No | Current borrower name |
| email | text | No | Borrower email |
| phone | text | No | Borrower phone |
| notes | text | No | Multi-purpose: condition, setup, lock reason, misc |
| returned | date | No | When returned (empty = active checkout) |
| last_updated | datetime | System | Auto-updated on every write, not displayed |
| sheets_row | integer | System | Sheets row index for this record; used as sync key to map SQLite rows to Sheets rows, not displayed |

### Derived Status (not stored)

| Status | Condition |
|--------|-----------|
| Locked | notes contains lock keyword (evaluated first) |
| Historical | Category = "Lease (Temp)" AND assigned_to set AND assigned_to ≠ "ready to assign" AND returned filled |
| Historical | Category = "Lease - Returned" AND assigned_to set AND assigned_to ≠ "ready to assign" (legacy category implies returned) |
| Checked Out | Category = "Lease (Temp)" AND assigned_to set AND assigned_to ≠ "ready to assign" AND returned empty |
| Not Assigned | assigned_to = "ready to assign" (explicit signal — see ADR 001 Addendum) |
| Uncategorized | No rule matched — row has unusual/partial data from Sheets |

> **Note:** "Not Assigned" was previously a fallthrough (anything not Locked/Historical/Checked Out). It is now an explicit check on `assigned_to = "ready to assign"`. The Return flow sets `assigned_to = "ready to assign"` on the new record it creates. See ADR 001 Addendum for full rationale.

---

## User Journeys

### J1: Check Out
Admin assigns a laptop to a student.

**Trigger:** Click [Check Out]
**Requires:** Select one laptop from table

**Task inputs:**
- targeted record

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
- Writes to existing targeted record: assigned_to, email, phone, last_updated
- Status derives to: "Checked Out"
- Validation: all required fields filled, laptop must be Not Assigned

---

### J2: Return
Admin processes a returned laptop and notes condition.

**Trigger:** Click [Return]
**Requires:** Select one laptop from table

**Task inputs:**
- targeted record

**Form inputs:**
- Notes (textarea — condition: Excellent / Good / Fair / Damaged, required)
- [MDM Wipe] button (non-functional placeholder)

**Auto-populated (read-only):**
- Serial # (from selected row)
- Type (from selected row)
- Assigned To (from selected row)

**On submit:**
1. Updates the existing Checked Out record: notes (appended), returned = today, last_updated → status derives to "Historical"
2. Creates a new record for the same device copying: label, type, serial_number, category, date_assigned, lease_end_date — leaving assigned_to, email, phone, notes, returned empty → status derives to "Not Assigned"
3. New record is appended as a new row in Google Sheets
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
- Validation: all required fields filled

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

### Row-Based Sync
Each Sheets row maps to exactly one SQLite record via `sheets_row` (the Sheets row index). Serial number is not the sync key — one device can have multiple rows in both Sheets and SQLite (one per checkout event).

### Flow
```
React → PATCH /api/assets/:id/checkout
      → Flask writes SQLite immediately
      → Flask queues Sheets API write (to the specific sheets_row)
      → Returns 200 to React

Background thread (every 3 min):
  → Poll Google Sheets (all rows)
  → For each row (keyed by sheets_row index):
    - Poll unchanged + DB differs  → frontend wins, retry Sheets write
    - Poll changed + DB unchanged  → external change, merge to SQLite
    - Poll changed + DB differs    → CONFLICT, Sheets wins, log it
```

### Startup Sync
On first boot (DB is empty), pull all rows from Sheets → SQLite to seed the database. On subsequent boots the DB already contains data; no full startup sync runs. Instead, the background poller fires immediately on startup (rather than waiting the first 3-minute interval) to pick up any Sheets changes that occurred while the server was down before serving the first request.

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
