# Category Column Split — Impact Analysis

**Date:** 2026-03-17
**Participants:** Ethan Davey, Claude Code

---

## Executive Summary

Splitting `category` into `ownership` and `asset_status` touches every layer of the stack: DB schema, sync mapping, status derivation logic, API validation, and the frontend form. The migration requires a brief planned downtime window — the app must be stopped before transforming Sheets to prevent the poller from writing stale data mid-migration. Column names and values are confirmed. No open decisions remain.

---

## Confirmed Column Definitions

| Column | Values | Meaning |
|--------|--------|---------|
| `ownership` | `Purchased` / `Lease` / `Donated` / `Returned` | How Pursuit acquired (or disposed of) the device |
| `asset_status` | `Temp` / `Historical` / `Unusable` / `Ready to Assign` | The device's current state in the checkout lifecycle |

`asset_status` is the raw stored column. The existing derived `status` field (computed by `derive_status()`, returned by the API) remains unchanged in name and values.

---

## What Currently Depends on `category`

### Backend — Critical

| File | What it does with `category` |
|------|------------------------------|
| `backend/models.py:36` | `_TABLE_DDL` — column in schema: `category TEXT NOT NULL` |
| `backend/models.py:78–102` | `derive_status()` — checks `category == 'Lease (Temp)'` and `category == 'Lease - Returned'` to determine Checked Out / Historical status |
| `backend/models.py:149` | `insert_asset()` — inserts `category` value |
| `backend/routes/assets.py:71` | `add_asset()` — `category` in required fields list |
| `backend/routes/assets.py:139` | Return journey — copies `category` from old record to new record; must now set both `ownership` and `asset_status` |

### Sync Layer

| File | What it does with `category` |
|------|------------------------------|
| `backend/sync/sheets.py:17–29` | `DESIRED_HEADERS` — `'Category'` is a column in the sheet layout |
| `backend/sync/sheets.py:31–44` | `HEADER_TO_FIELD` / `FIELD_TO_HEADER` — maps `'Category'` ↔ `'category'` |

### Frontend

| File | What it does with `category` |
|------|------------------------------|
| `frontend/src/components/forms/AddLaptopForm.jsx:4` | `CATEGORIES` constant — hardcoded list of allowed values |
| `AddLaptopForm.jsx:8,19,56–60` | Form state, validation, and `<select>` dropdown |

### Docs to update after implementation
- PRD data model table (both "Original Sheets Columns" and "SQLite / Google Sheets Columns" sections)
- PRD status derivation table (rules reference category values)
- PRD J3 Add Laptop form fields
- ADR 001 schema section, status rules, and `_TABLE_DDL` SQL block

---

## Sequence Diagram — Migration Execution Order

```
Developer (local)         Google Sheets          Fly.io App
      |                        |                      |
      |--- fly scale count 0 --------------------------->|
      |                        |              app stopped|
      |                        |                      |
      |--- run migrate_category_split.py              |
      |    reads all rows      |                      |
      |    splits category →   |                      |
      |    ownership +         |                      |
      |    asset_status        |                      |
      |    writes new headers  |                      |
      |    + transformed data  |                      |
      |<--- success            |                      |
      |                        |                      |
      |--- fly ssh console → rm assets.db ----------->|
      |<--- done                                      |
      |                                               |
      |--- deploy new code (models/sheets/routes/ui)->|
      |    init_db() runs — new schema                |
      |    count_assets() == 0 → _initial_sync()      |
      |    pulls from transformed Sheets → new DB     |
      |<--- app healthy, ~253 rows loaded             |
```

---

## Architecture Diagram — Before vs After

```
BEFORE

  Google Sheets                SQLite                  derive_status()
  ┌─────────────┐              ┌──────────────┐         checks:
  │  Category   │──── sync ───▶│  category    │──────▶  'Lease (Temp)'
  │  Lease (Temp│              │  TEXT NOT NULL│         'Lease - Returned'
  │  Lease - Ret│              └──────────────┘
  │  Purchased  │
  └─────────────┘


AFTER

  Google Sheets                SQLite                  derive_status()
  ┌──────────────┐             ┌──────────────┐         checks:
  │  Ownership   │──── sync ──▶│  ownership   │──────▶  ownership + asset_status
  │  Purchased   │             │  TEXT NOT NULL│         combinations replace
  │  Lease       │             ├──────────────┤         old category string checks
  │  Donated     │             │  asset_status│
  │  Returned    │             │  TEXT NOT NULL│
  ├──────────────┤             └──────────────┘
  │  Asset Status│──── sync ──▶
  │  Temp        │
  │  Historical  │
  │  Unusable    │
  │  Ready to    │
  │  Assign      │
  └──────────────┘
```

---

## Data Flow Diagram — Sheets Transform Script

```
stop app (fly scale count 0)
      │
      ▼
read_all_rows()
      │
      ▼
for each row:
  raw_category = row['Category']
      │
      ├── 'Lease (Temp)'     → ownership='Lease',     asset_status='Temp'
      ├── 'Lease - Returned' → ownership='Lease',     asset_status='Historical'
      ├── 'Purchased (Apple)'→ ownership='Purchased', asset_status=''  ← review
      ├── 'Staff'            → ownership='Donated',   asset_status=''  ← review
      └── anything else      → flag row for manual review before writing
      │
      ▼
rewrite sheet with new headers
(drop 'Category', add 'Ownership' + 'Asset Status')
preserve all other columns and row order
      │
      ▼
delete assets.db → deploy new code → DB rebuilds from Sheets
```

---

## Problem vs Solution

| Problem | Solution |
|---------|----------|
| `category` conflates ownership type and lifecycle state in one string | Split into `ownership` and `asset_status` with clean discrete values |
| `derive_status()` does string matching on a combined freeform value | Status logic checks two clean fields — easier to read and extend |
| AddLaptop form has one dropdown for a mixed concept | Two dropdowns with independent option lists |
| Return journey had no explicit `asset_status` to set on new record | Return journey now sets both `asset_status = 'Ready to Assign'` and `assigned_to = 'ready to assign'` |
| App could corrupt Sheets mid-migration if left running | App is stopped before migration script runs; no writes possible during transform |
| Future production sheet conversion requires the same transform | Migration script is reusable — only the sheet ID changes |

---

## DB Rebuild — Why You Need It (and Why It's Safe)

Adding two new columns and removing `category` requires a full schema replacement — SQLite doesn't support dropping columns cleanly. The cleanest approach for Fly.io is:

1. Delete `assets.db` from the Fly volume (`fly ssh console`)
2. Deploy new code
3. `count_assets() == 0` triggers `_initial_sync()` — full fresh pull from the already-transformed Sheets
4. DB is born with the new schema, populated correctly

This is safe because **Sheets is the source of truth**. The DB is a read cache + write buffer, not the authoritative record.

---

## Migration Script Strategy

`update_sheets_schema.py` is the direct precedent — reads all rows, remaps headers, preserves data, writes the sheet back in one call. `migrate_category_split.py` follows the same pattern with added parsing logic to split `category` into `ownership` + `asset_status`.

The script should include:
- A **dry-run mode** that prints the transformation without writing
- A **report of unrecognized category values** so edge cases can be reviewed before committing

Keeping the script in the repo root alongside `update_sheets_schema.py` is consistent with the existing pattern. The same script handles the production sheet conversion by pointing it at a different sheet ID.

---

## Side-by-Side: Code Changes Required

### `models.py` — schema + derive_status

```python
# BEFORE
_TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS assets (
        ...
        category TEXT NOT NULL,
        ...
    );
"""

def derive_status(row):
    category = (row['category'] or '').strip()
    if category == 'Lease - Returned' and ...:
        return 'Historical'
    if category == 'Lease (Temp)' and ...:
        ...

# AFTER
_TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS assets (
        ...
        ownership TEXT NOT NULL,
        asset_status TEXT NOT NULL,
        ...
    );
"""

def derive_status(row):
    ownership = (row['ownership'] or '').strip()
    asset_status = (row['asset_status'] or '').strip()
    if asset_status == 'Historical' and ...:
        return 'Historical'
    if asset_status == 'Temp' and ...:
        return 'Checked Out'
    if asset_status == 'Ready to Assign':
        return 'Not Assigned'
    ...
```

### `sheets.py` — headers + mapping

```python
# BEFORE
DESIRED_HEADERS = [..., 'Category', ...]
HEADER_TO_FIELD = {'Category': 'category', ...}

# AFTER
DESIRED_HEADERS = [..., 'Ownership', 'Asset Status', ...]
HEADER_TO_FIELD = {'Ownership': 'ownership', 'Asset Status': 'asset_status', ...}
```

### `routes/assets.py` — required fields + return journey

```python
# BEFORE
required = ['type', 'serial_number', 'category']
new_record = {'category': asset.get('category'), ...}

# AFTER
required = ['type', 'serial_number', 'ownership', 'asset_status']
new_record = {
    'ownership': asset.get('ownership'),
    'asset_status': 'Ready to Assign',
    'assigned_to': 'ready to assign',
    ...
}
```

### `AddLaptopForm.jsx` — form

```jsx
// BEFORE
const CATEGORIES = ['Lease Temp', 'Staff', 'Loaner', 'Other']
<select value={form.category} ...>

// AFTER
const OWNERSHIP_TYPES = ['Purchased', 'Lease', 'Donated', 'Returned']
const ASSET_STATUSES = ['Temp', 'Historical', 'Unusable', 'Ready to Assign']
<select value={form.ownership} ...>
<select value={form.asset_status} ...>
```
