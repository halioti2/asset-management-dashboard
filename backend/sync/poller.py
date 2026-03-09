"""
Background poller: every 3 minutes, compare Google Sheets data against
last-poll cache and SQLite to resolve conflicts.

Conflict rules:
  sheets unchanged, db changed  → frontend wins: retry write to sheets
  sheets changed, db unchanged  → external change: update sqlite
  sheets changed, db changed    → sheets wins: update sqlite, log conflict
"""
import json
import logging
import os
from datetime import datetime

from sync.sheets import read_all_rows, write_row
from models import upsert_asset_from_sheets, get_asset_by_sheets_row

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(os.getenv('DATA_DIR', os.path.dirname(__file__)), 'last_poll_cache.json')

# Fields used for change-detection (exclude id/status which are derived)
COMPARE_FIELDS = [
    'label', 'type', 'serial_number', 'category', 'date_assigned',
    'lease_end_date', 'assigned_to', 'email', 'phone', 'notes',
    'returned',
]


def _load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(data):
    try:
        with open(CACHE_PATH, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"poller: failed to save cache: {e}")


def _normalize(row):
    """Return only COMPARE_FIELDS from a row dict, all as strings."""
    return {k: str(row.get(k, '') or '') for k in COMPARE_FIELDS}


def _rows_equal(a, b):
    return _normalize(a) == _normalize(b)


def update_cache_for_row(asset):
    """Update the cache for a single row after a successful Sheets write.
    Prevents the poller from treating a user-reverted Sheets change as a
    failed local write and pushing stale data back to Sheets."""
    row_key = str(asset.get('sheets_row', ''))
    if not row_key:
        return
    cache = _load_cache()
    cache[row_key] = _normalize(asset)
    _save_cache(cache)


def force_sync_from_sheets():
    """
    One-shot: pull all rows from Sheets, overwrite SQLite, rebuild cache.
    Cache and DB are both keyed by sheets_row index so each Sheets row maps
    to exactly one SQLite record — duplicate serial numbers are handled correctly.
    """
    logger.info("force_sync: starting full sync from Google Sheets")
    try:
        sheets_rows = read_all_rows()
        new_cache = {}
        for row in sheets_rows:
            row_key = str(row.get('sheets_row', ''))
            if not row_key:
                continue
            upsert_asset_from_sheets(row)
            new_cache[row_key] = _normalize(row)
        _save_cache(new_cache)
        logger.info(f"force_sync: complete — {len(sheets_rows)} rows synced")
        return len(sheets_rows)
    except Exception as e:
        logger.error(f"force_sync: failed: {e}", exc_info=True)
        raise


def run_poll():
    """Execute one poll cycle. Called by APScheduler every 3 minutes.
    Each row is identified by its Sheets row index, not serial number,
    so multiple rows per serial (historical checkouts) are handled correctly."""
    logger.info("poller: starting poll cycle")
    try:
        cache = _load_cache()
        sheets_rows = read_all_rows()

        new_cache = {}
        for sheets_row in sheets_rows:
            serial = sheets_row.get('serial_number', '').strip()
            row_key = str(sheets_row.get('sheets_row', ''))
            if not row_key:
                continue

            prev = cache.get(row_key)
            db_row = get_asset_by_sheets_row(sheets_row.get('sheets_row'))
            new_cache[row_key] = _normalize(sheets_row)

            sheets_changed = prev is not None and not _rows_equal(sheets_row, prev)
            sheets_new = prev is None

            if sheets_new or sheets_changed:
                if db_row is None or _rows_equal(db_row, prev or {}):
                    upsert_asset_from_sheets(sheets_row)
                    logger.info(f"poller: merged external change for {serial!r} (row {row_key})")
                else:
                    upsert_asset_from_sheets(sheets_row)
                    logger.warning(
                        f"poller: CONFLICT for {serial!r} row {row_key} — sheets won. "
                        f"DB was: {_normalize(db_row)}, Sheets: {_normalize(sheets_row)}"
                    )
            else:
                if db_row and prev and not _rows_equal(db_row, prev):
                    try:
                        write_row(db_row)
                        logger.info(f"poller: synced local change to sheets for {serial!r} (row {row_key})")
                    except Exception as e:
                        logger.error(f"poller: failed to write {serial!r} row {row_key} to sheets: {e}")

        _save_cache(new_cache)
        logger.info(f"poller: poll cycle complete — processed {len(sheets_rows)} rows")
    except Exception as e:
        logger.error(f"poller: poll cycle failed: {e}", exc_info=True)
