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
from models import upsert_asset_from_sheets, get_asset_by_serial

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(os.path.dirname(__file__), 'last_poll_cache.json')

# Fields used for change-detection (exclude id/status which are derived)
COMPARE_FIELDS = [
    'label', 'type', 'serial_number', 'category', 'date_assigned',
    'lease_end_date', 'assigned_to', 'email', 'phone', 'notes',
    'returned', 'last_updated',
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


def run_poll():
    """Execute one poll cycle. Called by APScheduler every 3 minutes."""
    logger.info("poller: starting poll cycle")
    try:
        cache = _load_cache()
        sheets_rows = read_all_rows()

        new_cache = {}
        for sheets_row in sheets_rows:
            serial = sheets_row.get('serial_number', '').strip()
            if not serial:
                continue

            prev = cache.get(serial)
            db_row = get_asset_by_serial(serial)
            new_cache[serial] = _normalize(sheets_row)

            sheets_changed = prev is not None and not _rows_equal(sheets_row, prev)
            sheets_new = prev is None

            if sheets_new or sheets_changed:
                if db_row is None or _rows_equal(db_row, prev or {}):
                    # External change with no conflicting local change → merge
                    upsert_asset_from_sheets(sheets_row)
                    logger.info(f"poller: merged external change for {serial!r}")
                else:
                    # Both changed → sheets wins
                    upsert_asset_from_sheets(sheets_row)
                    logger.warning(
                        f"poller: CONFLICT for {serial!r} — sheets won. "
                        f"DB was: {_normalize(db_row)}, Sheets: {_normalize(sheets_row)}"
                    )
            else:
                # Sheets unchanged — check if db has pending writes
                if db_row and prev and not _rows_equal(db_row, prev):
                    try:
                        write_row(db_row)
                        logger.info(f"poller: synced local change to sheets for {serial!r}")
                    except Exception as e:
                        logger.error(f"poller: failed to write {serial!r} to sheets: {e}")

        _save_cache(new_cache)
        logger.info(f"poller: poll cycle complete — processed {len(sheets_rows)} rows")
    except Exception as e:
        logger.error(f"poller: poll cycle failed: {e}", exc_info=True)
