import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATABASE_PATH = os.getenv('DATABASE_PATH', './assets.db')

LOCK_KEYWORDS = ['locked', 'lock:', '[locked]', 'lock -']


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


_TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT,
        type TEXT NOT NULL,
        serial_number TEXT NOT NULL,
        sheets_row INTEGER,
        category TEXT NOT NULL,
        date_assigned TEXT,
        lease_end_date TEXT,
        assigned_to TEXT,
        email TEXT,
        phone TEXT,
        notes TEXT,
        returned TEXT,
        last_updated TEXT DEFAULT (datetime('now'))
    );
"""

_INDEX_DDL = """
    CREATE INDEX IF NOT EXISTS idx_assigned_to ON assets(assigned_to);
    CREATE INDEX IF NOT EXISTS idx_returned_assigned ON assets(returned, assigned_to);
    CREATE INDEX IF NOT EXISTS idx_lease_end_date ON assets(lease_end_date);
    CREATE INDEX IF NOT EXISTS idx_type ON assets(type);
    CREATE INDEX IF NOT EXISTS idx_serial ON assets(serial_number);
    CREATE INDEX IF NOT EXISTS idx_sheets_row ON assets(sheets_row);
"""


def init_db():
    conn = get_db()

    # Create table if it doesn't exist yet (new schema)
    conn.executescript(_TABLE_DDL)

    # Migration: old schema had UNIQUE on serial_number and no sheets_row column.
    # Must run before creating the sheets_row index.
    cols = [row[1] for row in conn.execute("PRAGMA table_info(assets)").fetchall()]
    if 'sheets_row' not in cols:
        logger.info("DB migration: removing UNIQUE from serial_number, adding sheets_row")
        conn.executescript(f"""
            ALTER TABLE assets RENAME TO assets_v1;
            {_TABLE_DDL}
            INSERT INTO assets
                (id, label, type, serial_number, category, date_assigned,
                 lease_end_date, assigned_to, email, phone, notes, returned, last_updated)
            SELECT id, label, type, serial_number, category, date_assigned,
                   lease_end_date, assigned_to, email, phone, notes, returned, last_updated
            FROM assets_v1;
            DROP TABLE assets_v1;
        """)
        logger.info("DB migration complete")

    conn.executescript(_INDEX_DDL)
    conn.commit()
    conn.close()


def derive_status(row):
    """Derive status from asset fields — pure function."""
    notes = (row['notes'] or '').lower()
    category = (row['category'] or '').strip()
    assigned_to = (row['assigned_to'] or '').strip()
    returned = row['returned'] or ''

    # Check for lock keywords in notes
    for keyword in LOCK_KEYWORDS:
        if keyword in notes:
            return 'Locked'

    if category == 'Lease - Returned' and assigned_to and assigned_to.lower() != 'ready to assign':
        return 'Historical'

    if category == 'Lease (Temp)' and assigned_to and assigned_to.lower() != 'ready to assign':
        if returned:
            return 'Historical'
        else:
            return 'Checked Out'

    if assigned_to.lower() == 'ready to assign':
        return 'Not Assigned'

    return 'Uncategorized'


def row_to_dict(row):
    """Convert sqlite3.Row to dict with status."""
    d = dict(row)
    d['status'] = derive_status(d)
    return d


# ── CRUD helpers ──────────────────────────────────────────────────────────────

def get_all_assets():
    conn = get_db()
    rows = conn.execute("SELECT * FROM assets ORDER BY id").fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_asset_by_id(asset_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def get_asset_by_serial(serial_number):
    conn = get_db()
    row = conn.execute("SELECT * FROM assets WHERE serial_number = ?", (serial_number,)).fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def get_asset_by_sheets_row(sheets_row):
    conn = get_db()
    row = conn.execute("SELECT * FROM assets WHERE sheets_row = ?", (sheets_row,)).fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def insert_asset(data):
    conn = get_db()
    now = datetime.utcnow().isoformat()
    cursor = conn.execute("""
        INSERT INTO assets
            (label, type, serial_number, sheets_row, category, date_assigned, lease_end_date,
             assigned_to, email, phone, notes, returned, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('label', ''),
        data['type'],
        data['serial_number'],
        data.get('sheets_row'),
        data['category'],
        data.get('date_assigned', ''),
        data.get('lease_end_date', ''),
        data.get('assigned_to', ''),
        data.get('email', ''),
        data.get('phone', ''),
        data.get('notes', ''),
        data.get('returned', ''),
        now,
    ))
    conn.commit()
    asset_id = cursor.lastrowid
    conn.close()
    return get_asset_by_id(asset_id)


def update_asset(asset_id, fields):
    """Update arbitrary fields on an asset. fields is a dict."""
    if not fields:
        return get_asset_by_id(asset_id)
    fields['last_updated'] = datetime.utcnow().isoformat()
    set_clause = ', '.join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [asset_id]
    conn = get_db()
    conn.execute(f"UPDATE assets SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return get_asset_by_id(asset_id)


def upsert_asset_from_sheets(data):
    """Insert or update asset from Sheets sync, keyed on sheets_row.
    Falls back to serial_number lookup for records not yet assigned a sheets_row."""
    sheets_row = data.get('sheets_row')
    existing = get_asset_by_sheets_row(sheets_row) if sheets_row else None
    if existing is None and data.get('serial_number'):
        # Fallback: find a record with no sheets_row assigned for this serial
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM assets WHERE serial_number = ? AND sheets_row IS NULL",
            (data['serial_number'],)
        ).fetchone()
        conn.close()
        existing = row_to_dict(row) if row else None
    if existing:
        fields = {k: v for k, v in data.items() if k != 'serial_number'}
        return update_asset(existing['id'], fields)
    else:
        return insert_asset(data)


def count_assets():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    conn.close()
    return count
