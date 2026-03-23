#!/usr/bin/env python3
"""
Migrate Google Sheets: split 'Category' into 'Ownership' + 'Asset Status'.

Usage:
  python migrate_category_split.py            # dry run (no writes)
  python migrate_category_split.py --execute  # write to sheet

Works against both the original schema (pre-Email/Phone/Last Updated)
and the current schema — uses header-based lookup, not positional.
The output always matches the full desired header layout.
"""

import os
import sys
import json
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_NAME = 'Distribution Tracker'

DESIRED_HEADERS = [
    'Label',
    'Type',
    'Assigned To',
    'Email',
    'Phone',
    'Serial #',
    'Date Assigned',
    'Ownership',
    'Asset Status',
    'Lease End Date',
    'Notes',
    'Returned',
    'Last Updated',
]

# Confirmed ownership mappings (see ADR 003)
CATEGORY_TO_OWNERSHIP = {
    'Lease (Temp)':      'Lease',
    'Lease (Own)':       'Lease',
    'Lease - Returned':  'Lease',
    'Purchased (Apple)': 'Purchased',
    'Purchased (Dell)':  'Purchased',
    'Donated':           'Donated',
    'Returned':          'Returned',
    'Unusable':          '',          # ownership left blank pending manual review
}


def _derive_asset_status(category, assigned_to, returned):
    """Derive asset_status from category + assigned_to + returned."""
    cat = (category or '').strip()
    assigned = (assigned_to or '').strip().lower()
    ret = (returned or '').strip()

    # Fixed mappings
    if cat in ('Lease - Returned', 'Returned'):
        return 'Historical'
    if cat == 'Unusable':
        return 'Unusable'

    # Derived from row state (Lease (Temp), Lease (Own), Purchased (Apple/Dell), Donated)
    if ret:
        return 'Historical'
    if assigned == 'ready to assign':
        return 'Ready to Assign'
    if assigned:
        return 'Temp'
    # assigned_to is blank — status unknown, do not assume Ready to Assign
    return ''


def _get_service():
    creds = Credentials.from_service_account_info(
        json.loads(os.getenv('GOOGLE_SHEETS_CREDENTIALS')),
        scopes=SCOPES,
    )
    return build('sheets', 'v4', credentials=creds, cache_discovery=False)


def _read_sheet(service, sheet_id):
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=SHEET_NAME,
    ).execute()
    return result.get('values', [])


def _write_sheet(service, sheet_id, values):
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=SHEET_NAME,
        valueInputOption='RAW',
        body={'values': values},
    ).execute()


def run(dry_run=True):
    sheet_id = os.getenv('GOOGLE_SHEET_ID', '').strip()
    if not sheet_id:
        print('ERROR: GOOGLE_SHEET_ID not set in .env')
        sys.exit(1)

    service = _get_service()
    values = _read_sheet(service, sheet_id)
    if not values:
        print('ERROR: Sheet is empty')
        sys.exit(1)

    current_headers = values[0]
    data_rows = values[1:]
    old_idx = {h: i for i, h in enumerate(current_headers)}

    print(f"Current headers: {current_headers}")
    print(f"Rows to transform: {len(data_rows)}")
    print(f"Mode: {'DRY RUN (no writes)' if dry_run else 'EXECUTE (will write to sheet)'}")
    print()

    if 'Category' not in old_idx:
        print('No Category column found — sheet may already be migrated.')
        return

    unrecognized = {}
    new_rows = []

    for i, row in enumerate(data_rows):
        padded = row + [''] * (len(current_headers) - len(row))

        def get(header):
            idx = old_idx.get(header)
            return padded[idx].strip() if idx is not None and idx < len(padded) else ''

        category    = get('Category')
        assigned_to = get('Assigned To')
        returned    = get('Returned')

        ownership   = CATEGORY_TO_OWNERSHIP.get(category)
        if ownership is None:
            unrecognized.setdefault(category, []).append(i + 2)  # 1-based + header
            ownership = ''

        asset_status = _derive_asset_status(category, assigned_to, returned)

        # Build new row against DESIRED_HEADERS
        # Values come from old columns by name; Ownership + Asset Status are new
        new_row = []
        for header in DESIRED_HEADERS:
            if header == 'Ownership':
                new_row.append(ownership)
            elif header == 'Asset Status':
                new_row.append(asset_status)
            else:
                idx = old_idx.get(header)
                val = padded[idx] if idx is not None and idx < len(padded) else ''
                new_row.append(val)

        serial = get('Serial #') or f'row {i + 2}'
        print(f"  Row {i+2:3d}  [{serial:30s}]  {category!r:25s}  →  ownership={ownership!r:12s}  asset_status={asset_status!r}")
        new_rows.append(new_row)

    print()

    if unrecognized:
        print('UNRECOGNIZED category values (not in mapping table):')
        for cat, rows in unrecognized.items():
            print(f"  {cat!r:30s}  rows: {rows}")
        print()

    print(f"Summary: {len(data_rows)} rows transformed, {len(unrecognized)} unrecognized categories")

    if dry_run:
        print()
        print('DRY RUN complete — no changes written. Re-run with --execute to apply.')
        return

    all_data = [DESIRED_HEADERS] + new_rows
    _write_sheet(service, sheet_id, all_data)
    print(f'Sheet updated successfully with {len(new_rows)} rows.')


if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv

    # Optional overrides: --sheet-id <id> and --sheet-name <name>
    args = sys.argv[1:]
    if '--sheet-id' in args:
        idx = args.index('--sheet-id')
        os.environ['GOOGLE_SHEET_ID'] = args[idx + 1]
    if '--sheet-name' in args:
        idx = args.index('--sheet-name')
        SHEET_NAME = args[idx + 1]

    run(dry_run=dry_run)
