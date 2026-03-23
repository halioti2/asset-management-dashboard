# ADR 003: Split `category` into `ownership` and `asset_status`

**Status:** Amended
**Date:** 2026-03-17
**Amended:** 2026-03-23
**Participants:** Ethan Davey, Victoria, Claude Code

---

## Decision

Replace the single `category` column (in both SQLite and Google Sheets) with two columns:

| Column | Values | Meaning |
|--------|--------|---------|
| `ownership` | `Purchased` / `Lease-Temp` / `Lease-Own` / `Donated` / `Returned` | How Pursuit acquired (or disposed of) the device |
| `asset_status` | `Assigned` / `Historical` / `Unusable` / `Ready to Assign` | The device's current state in the checkout lifecycle |

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

1. **Dry run first** — run `migrate_category_split.py` (no flags) against a copy of the sheet to print every row's transformation without writing anything. Review for unrecognized category values before proceeding.
2. Run `migrate_category_split.py --execute` to transform Google Sheets in-place — splits `category` into `ownership` + `asset_status`, rewrites the sheet with new headers.
3. Update `GOOGLE_SHEET_ID` in Fly secrets (`fly secrets set GOOGLE_SHEET_ID=<id>`) if pointing at a new sheet. This triggers a rolling restart of the existing machine — do NOT use `fly scale count 0`, which destroys the machine and causes deployment issues.
4. Deploy updated code — `fly deploy` rolls new code onto the running machine in-place.
5. After deploy, delete the DB and cache via SSH using a Python one-liner (shell commands do not work over Fly SSH):
   ```
   fly ssh console -a <app> --command "python3 -c \"import os; [os.remove(f) for f in ['/data/assets.db', '/data/last_poll_cache.json'] if os.path.exists(f)]; print('done')\""
   ```
6. Seed the DB by calling `init_db()` then `force_sync_from_sheets()` directly over SSH before restarting, to avoid a gunicorn fork/thread deadlock on first boot with an empty DB:
   ```
   fly ssh console -a <app> --command "python3 -c \"import sys; sys.path.insert(0,'/app'); from models import init_db; init_db(); from sync.poller import force_sync_from_sheets; n = force_sync_from_sheets(); print(f'{n} rows synced')\""
   ```
7. Restart the machine (`fly machine restart <id>`) — gunicorn boots cleanly against the already-populated DB and health checks pass.

Sheets is the source of truth, so deleting and rebuilding the DB is safe. Do not scale to 0 at any point — it is unnecessary and breaks the SSH-based DB reset in step 5.

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
| `Lease (Temp)` | `Lease-Temp` | derived |
| `Lease (Own)` | `Lease-Own` | derived |
| `Lease - Returned` | *(blank)* | `Historical` |
| `Purchased (Apple)` | `Purchased` | derived |
| `Purchased (Dell)` | `Purchased` | derived |
| `Donated` | `Donated` | derived |
| `Returned` | `Returned` | `Historical` |
| `Unusable` | *(blank)* | `Unusable` |

**"Derived" asset_status logic** (applied to all rows marked "derived" above):
- `returned` date is filled → `Historical`
- `assigned_to` is set and ≠ "ready to assign" → `Assigned`
- `assigned_to` = "ready to assign" → `Ready to Assign`
- `assigned_to` is empty → **data quality gap** — the device has no confirmed status. Should be investigated and corrected manually; do NOT treat blank as "ready to assign"

> **Known migration issue:** The initial run of `migrate_category_split.py` incorrectly treated empty `assigned_to` as `Ready to Assign`. This caused 26 rows to be mislabeled, including at least one confirmed checked-out device (J2JTGQCYNY / Andrew Tien). Those rows require manual review. The script has not been corrected because it is a one-time artifact, but any future reuse must fix this rule first.

**Notes:**
- `Lease (Own)` was an undocumented category in the sheet — permanent-ish lease assignments. Maps to `Lease-Own`.
- `Lease - Returned` ownership is left blank — the original category cannot distinguish between Lease-Temp and Lease-Own, so these rows require manual review.
- `Unusable` appeared as a category value but is semantically an `asset_status`. `ownership` is left blank for these 3 rows pending manual review.
- The script flags any unrecognized category values in its dry-run output rather than silently dropping them.

---

## Return Journey Behavior

When the Return flow creates the new "available" record, it must populate both fields explicitly:

- `asset_status = "Ready to Assign"`
- `assigned_to = "ready to assign"`

The `assigned_to` magic string is preserved as-is for now — cleaning that up is a separate future task. Both fields must be written together to keep `derive_status()` and the new `asset_status` column in sync.

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-03-23 | Ethan Davey, Victoria | Reviewed ownership values with Victoria. Split `Lease` into `Lease-Temp` and `Lease-Own` — the old category names map directly to these. `Lease - Returned` ownership left blank (ambiguous, requires manual review). Renamed `asset_status` value `Temp` → `Assigned` for clarity. |
| 2026-03-23 | Ethan Davey, Claude Code | Corrected Migration Strategy steps based on what actually worked in practice: removed `fly scale count 0` (destroys machine, breaks SSH reset), added SSH Python one-liner for DB deletion, added pre-restart DB seed step to avoid gunicorn fork/thread deadlock on empty DB. |

---

## What Doesn't Change

- The derived `status` field name and its values (`Checked Out`, `Not Assigned`, `Historical`, `Locked`, `Uncategorized`)
- The `returned` date column
- Sync architecture, conflict resolution, polling interval
- All API endpoint paths
