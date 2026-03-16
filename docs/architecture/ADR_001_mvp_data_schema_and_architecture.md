# ADR 001: MVP Data Schema & Architecture

**Status:** Pending Implementation
**Date:** 2026-02-26
**Participants:** Ethan Davey, Claude Code

---

## Executive Summary

This ADR documents the complete data schema, architecture decisions, and UI-to-database mappings for the Asset Management Dashboard MVP. Key decisions include:
- SQLite as persistent single-user database with Fly.io hosting
- Google Sheets as secondary sync source (3-minute polling)
- Flask backend for API + sync logic
- React frontend with 5 user journeys
- Conflict resolution strategy for sync discrepancies

---

## Problem Statement

The original Google Sheets data model does not fully match the UI requirements from the 5 user journeys. Specifically:
1. "Notes" field in Sheets needs to be split into 4 distinct note types
2. "Assigned To" field needs to be renamed to "Student Name" for clarity
3. New fields (Email, Phone) need to be added to track checkout info
4. Status is derived (not stored), requiring backend logic
5. Need to handle sync between Sheets and SQLite with conflict resolution

---

## Data Schema

### Google Sheets Columns (current state - minimal updates needed)

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| Label | Text | Yes | Equipment identifier (e.g., "MacBook Air #1") |
| Type | Text | Yes | Equipment type (dropdown: MacBook Air, MacBook Pro, Dell XPS, iPad, etc.) |
| Serial # | Text | Yes | Unique serial number |
| Category | Text | Yes | Category (dropdown: Laptop, iPad, Other) |
| Date Assigned | Date | Yes | When equipment was first assigned to inventory |
| Lease End Date | Date | Yes | When the lease expires |
| Assigned To | Text | No | Current person assigned to equipment |
| Email | Text | No | Email of student/borrower |
| Phone | Text | No | Phone number of student/borrower |
| Notes | Text | No | Multi-purpose notes (condition, setup, lock reasons, misc) |
| Returned | Date | No | When equipment was actually returned (marks historical record) |
| Last Updated | DateTime | System | Timestamp of last edit (tracked but not displayed in UI) |

### Derived Fields (calculated on-the-fly, not stored)

**Status:** Determined by the following rules:
- **Locked**: Notes contains lock keyword (checked first)
- **Historical**: Category = "Lease - Returned" OR (Category = "Lease (Temp)" AND Assigned To set AND Assigned To ≠ "ready to assign" AND Returned filled)
- **Checked Out**: Category = "Lease (Temp)" AND Assigned To set AND Assigned To ≠ "ready to assign" AND Returned empty
- **Not Assigned**: Assigned To = "ready to assign" (explicit signal — see ADR 001 Addendum below)
- **Uncategorized**: All other rows (no matching rule — see ADR 001 Addendum below)

---

## ADR 001 Addendum: Not Assigned Source of Truth (2026-03-09)

### Decision

`"ready to assign"` in the `assigned_to` column is the canonical signal for "Not Assigned" status. Rows that do not match any status rule are classified as `"Uncategorized"` rather than silently falling through to "Not Assigned."

### Supersedes

The original rule: `Not Assigned = returned empty AND (assigned_to empty OR assigned_to = "ready to assign")`

### Rationale

The original fallthrough approach caused edge cases from real Sheets data (unusual category values, partial rows, legacy formats) to appear as "Not Assigned" in the filter, making the filter unreliable. Using `"ready to assign"` as an explicit marker is consistent with how the spreadsheet was already being managed and gives the filter a single, trustworthy source of truth.

### Consequences

- Rows that don't match any rule surface as "Uncategorized" — visible and filterable, not hidden
- The Return flow must set `assigned_to = "ready to assign"` on the new record it creates so it appears correctly as Not Assigned
- The Checkout validation (`derive_status != 'Not Assigned'`) continues to work unchanged — only rows explicitly marked "ready to assign" are eligible for checkout

---

## Database Implementation

### SQLite Schema

```sql
CREATE TABLE assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  label TEXT NOT NULL,
  type TEXT NOT NULL,
  serial_number TEXT UNIQUE NOT NULL,
  category TEXT NOT NULL,
  date_assigned DATE NOT NULL,
  lease_end_date DATE NOT NULL,
  assigned_to TEXT,
  email TEXT,
  phone TEXT,
  notes TEXT,
  returned DATE,
  last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_assigned_to ON assets(assigned_to);
CREATE INDEX idx_status ON assets(returned, assigned_to);
CREATE INDEX idx_lease_end_date ON assets(lease_end_date);
CREATE INDEX idx_type ON assets(type);
```

---

## UI Mapping

### Frontend Display Table Columns

1. Label
2. Type
3. Serial #
4. Status (derived)
5. Assigned To
6. Lease End Date
7. Notes
8. Returned

### Filters Available

- **Status**: Checked Out / Not Assigned / Historical / Locked
- **Assigned To**: Dropdown of all assigned users
- **Type**: Dropdown of equipment types
- **Date Range**: Before/After Lease End Date

---

## User Journeys & Form Fields

### Journey 1: Check Out
- **Trigger**: Click [Check Out] button
- **Form Fields**:
  - Assigned To (text input)
  - Email (email input)
  - Phone (tel input)
  - Duration Needed (dropdown: 1 day, 1 semester) [UI only, not stored]
  - Serial Number (auto-populated, read-only)
  - Model/Type (auto-populated, read-only)
  - Return Date (calculated, read-only)
- **Data Updated**: Assigned To, Email, Phone, Returned (calculated based on duration)

### Journey 2: Return
- **Trigger**: Click [Return] button
- **Form Fields**:
  - Notes (textarea for condition notes)
  - Serial Number (auto-populated, read-only)
  - Type (auto-populated, read-only)
  - Assigned To (auto-populated, read-only)
- **Data Updated**: Notes (appended with condition info), Returned (set to today)

### Journey 3: Add Laptop
- **Trigger**: Click [Add Laptop] button
- **Form Fields**:
  - Label (text input)
  - Type (dropdown)
  - Serial # (text input)
  - Category (dropdown)
  - Date Assigned (date picker)
  - Lease End Date (date picker)
  - Notes (textarea, optional - for setup notes)
- **Data Updated**: Creates new record with all fields

### Journey 4: Lock
- **Trigger**: Click [Lock] button
- **Form Fields**:
  - Notes (textarea for lock reason)
  - Serial Number (auto-populated, read-only)
  - Type (auto-populated, read-only)
- **Data Updated**: Notes (appended with lock reason)

### Journey 5: Update Misc Notes
- **Trigger**: Click [Update Misc Notes] button
- **Form Fields**:
  - Notes (textarea for editing/appending notes)
- **Data Updated**: Notes for selected records, Last Updated timestamp

---

## API Endpoints

### GET /api/assets
Returns all assets, filtered by query parameters.

**Query Parameters**:
- `status`: "checked_out" | "not_assigned" | "historical" | "locked"
- `assigned_to`: Filter by assigned user
- `type`: Filter by equipment type
- `lease_end_date_before`: ISO date
- `lease_end_date_after`: ISO date

**Response**: Array of asset objects with derived Status field

### POST /api/assets
Create new asset.

**Request Body**:
```json
{
  "label": "MacBook Air #2",
  "type": "MacBook Air",
  "serial_number": "ABC123XYZ",
  "category": "Laptop",
  "date_assigned": "2026-02-26",
  "lease_end_date": "2027-02-26",
  "notes": "Optional setup notes"
}
```

### PATCH /api/assets/{id}
Update existing asset.

**Request Body**: Any of the non-derived fields

### PATCH /api/assets/{id}/checkout
Special endpoint for Check Out journey.

**Request Body**:
```json
{
  "assigned_to": "John Doe",
  "email": "john@example.com",
  "phone": "555-1234",
  "returned": "2026-03-26"
}
```

### PATCH /api/assets/{id}/return
Special endpoint for Return journey.

**Request Body**:
```json
{
  "notes": "Excellent condition",
  "returned": "2026-02-26"
}
```

---

## Sync Architecture: SQLite ↔ Google Sheets

### Problem Scenarios & Resolution

**Scenario 1: Frontend change not yet synced to Sheets**
- User updates asset → SQLite updated immediately
- Backend syncs to Sheets API
- If poll detects poll data unchanged since last poll → Frontend wins
- Action: Retry sync to Sheets

**Scenario 2: Different records changed (external + local)**
- User changed Record A locally
- Someone else changed Record B in Sheets
- Poll detects Record B changed (Record A unchanged)
- Action: Update SQLite with Record B change, keep Record A local

**Scenario 3: Same record changed both places (CONFLICT)**
- Poll data differs from previous poll AND differs from SQLite
- Indicates both external and local changes on same record
- Resolution: **Sheets wins** (external source is authoritative)
- Action: Overwrite SQLite with Sheets value, log conflict

### Polling Logic

**Scheduled Function (every 3 minutes)**:
```
1. Poll Google Sheets API for all assets
2. For each asset in poll:
   a. Get previous_poll_value from cache
   b. Get current_sqlite_value from DB
   c. Get current_poll_value from API response

   d. If current_poll_value == previous_poll_value:
      - Poll unchanged
      - If current_sqlite_value != current_poll_value:
        - Frontend changed it, retry sync to Sheets

   e. Else (poll changed):
      - If current_sqlite_value == previous_poll_value:
        - External change only, merge to SQLite
      - Else:
        - CONFLICT: Both changed, Sheets wins
        - Update SQLite with current_poll_value
        - Log conflict

   f. Store current_poll_value for next poll comparison

3. Store updated cache
```

### Startup Behavior

`_initial_sync()` runs on every boot but only does work when `count_assets() == 0` (DB is empty). On first boot against a fresh DB it pulls all rows from Sheets into SQLite. On all subsequent boots it skips immediately.

The background poller is configured with `next_run_time=datetime.now(timezone.utc)` so it fires once immediately on startup before settling into its 3-minute interval. This ensures any Sheets changes made while the server was down are reflected in SQLite before the first request is served, without performing a full blind overwrite.

`force_sync_from_sheets()` exists as an admin escape hatch (exposed via `POST /api/assets/sync`) but is not called automatically. It performs a blind overwrite of SQLite with current Sheets state — no conflict check — and should only be used manually when a known drift needs correcting.

---

## Tech Stack Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Frontend | React | Multi-section layout, form+table interaction, select-and-populate pattern requires React UX |
| Backend | Flask (Python) | Simple, fast to develop, good for single-user, easy to integrate with Google Sheets API |
| Database | SQLite | Persistent single-user database, perfect for Flask, resolves consistency issues with Sheets-only approach |
| Hosting | Fly.io | Supports Flask + persistent SQLite, free tier available, good for single-user MVP |
| Google Sheets | API Integration | 3-minute polling, sync source for auditing/sharing |
| Version Control | Git | Standard practice |

---

## Google Sheets Schema Update Required

**Action Item**: Minimal updates to existing Google Sheet:
- Add "Email" column (if not already present)
- Add "Phone" column (if not already present)
- Add "Last Updated" column (system-managed)

**Note**: "Assigned To" and "Returned" columns remain as-is. All note types (condition, setup, lock reason, misc) are appended to the single "Notes" column.

---

## Unresolved Questions / Future Work

- How should app handle Google Sheets API rate limits?
- Should there be an audit log UI for conflict/sync events?
- How to handle multi-instance deployment (Fly.io scaling)?
- Offline support (sync when back online)?

---

## Sign-Off

**Proposed by**: Claude Code
**Reviewed by**: [Pending]
**Approved by**: [Pending]
