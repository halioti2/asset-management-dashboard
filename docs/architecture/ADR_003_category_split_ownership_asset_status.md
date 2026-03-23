# ADR 003: Split `category` into `ownership` and `asset_status`

**Status:** Implemented
**Date:** 2026-03-17
**Participants:** Ethan Davey, Claude Code

---

## Decision

Replace the single `category` column (in both SQLite and Google Sheets) with two columns:

| Column | Values | Meaning |
|--------|--------|---------|
| `ownership` | `Purchased` / `Lease` / `Donated` / `Returned` | How Pursuit acquired (or disposed of) the device |
| `asset_status` | `Temp` / `Historical` / `Unusable` / `Ready to Assign` | The device's current state in the checkout lifecycle |

`asset_status` is the raw stored column. The existing derived `status` field (computed by `derive_status()` and returned by the API) remains unchanged in name.

---

## Why

`category` currently conflates two distinct concepts — ownership type and lifecycle state — in a single freeform string (e.g. `Lease (Temp)`, `Lease - Returned`). This makes status derivation brittle and the data model harder to extend.

Separating them makes each field independently queryable, easier to filter on, and clearer to manage when adding new devices.

---

## Completion

- **Migration completed:** 2026-03-17
- **Sheet migrated:** `1RitKbGmGE_Nwyw_HZk3pqigQmc-h77Qo4nwH7ExvSUc` (Pursuit production sheet)
- **Code deployed to:** Fly.io machine `7817246a0d6978`
- **Rows transformed:** 256 rows, 0 unrecognized categories
- **Known data gaps:** ~25 rows have blank `asset_status` (Lease Own + Donated rows with empty `assigned_to`) — these surface as Uncategorized and require manual data review

---

## Migration Strategy

1. **Dry run first** — run `migrate_category_split.py --dry-run` against the sheet to print every row's transformation without writing anything. Review the output for any unrecognized category values and resolve them before proceeding.
2. **Stop the app** (`fly scale count 0`) — prevents the poller or any user action from writing stale data to Sheets during the transform
3. Run `migrate_category_split.py` to transform the Google Sheets column in-place — splits `category` into `ownership` + `asset_status`, rewrites the sheet with new headers
4. Delete `assets.db` from the Fly.io volume (`fly ssh console`)
5. Deploy updated code (schema, sync mapping, status logic, API, frontend) — this brings the app back up
6. On startup, `count_assets() == 0` triggers `_initial_sync()` — DB is rebuilt fresh from the transformed sheet

Sheets is the source of truth, so deleting and rebuilding the DB is safe. Total downtime (steps 2–5) is the script runtime plus deploy time (~1–2 minutes).

The same migration script can be reused for the production sheet conversion by pointing it at a different sheet ID.

---

## What Changes

- `models.py` — schema DDL, `derive_status()` logic, `insert_asset()`
- `sheets.py` — `DESIRED_HEADERS`, `HEADER_TO_FIELD` / `FIELD_TO_HEADER`
- `routes/assets.py` — required field validation, return journey record copy
- `AddLaptopForm.jsx` — Category dropdown splits into two dropdowns

---

## Category Migration Mappings

The following mappings were confirmed by running a dry-run against the dev sheet. These are the rules `migrate_category_split.py` uses to populate `ownership` and `asset_status` from the old `category` value.

| Old `category` | `ownership` | `asset_status` |
|----------------|-------------|----------------|
| `Lease (Temp)` | `Lease` | derived |
| `Lease (Own)` | `Lease` | derived |
| `Lease - Returned` | `Lease` | `Historical` |
| `Purchased (Apple)` | `Purchased` | derived |
| `Purchased (Dell)` | `Purchased` | derived |
| `Donated` | `Donated` | derived |
| `Returned` | `Returned` | `Historical` |
| `Unusable` | *(blank)* | `Unusable` |

**"Derived" asset_status logic** (applied to all rows marked "derived" above):
- `returned` date is filled → `Historical`
- `assigned_to` is set and ≠ "ready to assign" → `Temp`
- `assigned_to` = "ready to assign" → `Ready to Assign`
- `assigned_to` is empty → **data quality gap** — the device has no confirmed status. Should be investigated and corrected manually; do NOT treat blank as "ready to assign"

> **Known migration issue:** The initial run of `migrate_category_split.py` incorrectly treated empty `assigned_to` as `Ready to Assign`. This caused 26 rows to be mislabeled, including at least one confirmed checked-out device (J2JTGQCYNY / Andrew Tien). Those rows require manual review. The script has not been corrected because it is a one-time artifact, but any future reuse must fix this rule first.

**Notes:**
- `Lease (Own)` was an undocumented category in the sheet — permanent-ish lease assignments. Treated identically to `Lease (Temp)` for migration purposes.
- `Unusable` appeared as a category value but is semantically an `asset_status`. `ownership` is left blank for these 3 rows pending manual review.
- The script flags any unrecognized category values in its dry-run output rather than silently dropping them.

---

## Return Journey Behavior

When the Return flow creates the new "available" record, it must populate both fields explicitly:

- `asset_status = "Ready to Assign"`
- `assigned_to = "ready to assign"`

The `assigned_to` magic string is preserved as-is for now — cleaning that up is a separate future task. Both fields must be written together to keep `derive_status()` and the new `asset_status` column in sync.

---

## What Doesn't Change

- The derived `status` field name and its values (`Checked Out`, `Not Assigned`, `Historical`, `Locked`, `Uncategorized`)
- The `returned` date column
- Sync architecture, conflict resolution, polling interval
- All API endpoint paths
