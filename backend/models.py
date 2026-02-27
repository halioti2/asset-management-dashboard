import sqlite3
import os
from datetime import datetime

DATABASE_PATH = os.getenv('DATABASE_PATH', './assets.db')

LOCK_KEYWORDS = ['locked', 'lock:', '[locked]', 'lock -']


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            type TEXT NOT NULL,
            serial_number TEXT UNIQUE NOT NULL,
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

        CREATE INDEX IF NOT EXISTS idx_assigned_to ON assets(assigned_to);
        CREATE INDEX IF NOT EXISTS idx_returned_assigned ON assets(returned, assigned_to);
        CREATE INDEX IF NOT EXISTS idx_lease_end_date ON assets(lease_end_date);
        CREATE INDEX IF NOT EXISTS idx_type ON assets(type);
    """)
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

    if category == 'Lease Temp' and assigned_to and assigned_to.lower() != 'ready to assign':
        if returned:
            return 'Historical'
        else:
            return 'Checked Out'

    return 'Not Assigned'


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


def insert_asset(data):
    conn = get_db()
    now = datetime.utcnow().isoformat()
    cursor = conn.execute("""
        INSERT INTO assets
            (label, type, serial_number, category, date_assigned, lease_end_date,
             assigned_to, email, phone, notes, returned, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('label', ''),
        data['type'],
        data['serial_number'],
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
    """Insert or update asset from Sheets sync (keyed on serial_number)."""
    existing = get_asset_by_serial(data['serial_number'])
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
