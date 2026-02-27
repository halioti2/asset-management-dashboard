import os
import json
import logging
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_NAME = 'Distribution Tracker'

# Desired final column order
DESIRED_HEADERS = [
    'Label',
    'Type',
    'Assigned To',
    'Email',
    'Phone',
    'Serial #',
    'Date Assigned',
    'Category',
    'Lease End Date',
    'Notes',
    'Returned',
    'Last Updated',
]

HEADER_TO_FIELD = {
    'Label':          'label',
    'Type':           'type',
    'Assigned To':    'assigned_to',
    'Email':          'email',
    'Phone':          'phone',
    'Serial #':       'serial_number',
    'Date Assigned':  'date_assigned',
    'Category':       'category',
    'Lease End Date': 'lease_end_date',
    'Notes':          'notes',
    'Returned':       'returned',
    'Last Updated':   'last_updated',
}
FIELD_TO_HEADER = {v: k for k, v in HEADER_TO_FIELD.items()}


def _get_sheet_id():
    sheet_id = os.getenv('GOOGLE_SHEET_ID', '').strip()
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID not set in .env")
    return sheet_id


def get_service():
    creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS not set in .env")
    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('sheets', 'v4', credentials=credentials)


def _read_all_values(service, sheet_id):
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=SHEET_NAME,
    ).execute()
    return result.get('values', [])


def _get_headers(service, sheet_id):
    """Return the current header row as a list."""
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!1:1",
    ).execute()
    return result.get('values', [[]])[0]


def ensure_schema():
    """
    If the sheet is missing Email, Phone, or Last Updated columns,
    rewrite the entire sheet with the correct header layout,
    preserving all existing data in the right columns.
    """
    service = get_service()
    sheet_id = _get_sheet_id()
    values = _read_all_values(service, sheet_id)
    if not values:
        logger.warning("ensure_schema: sheet is empty, nothing to do")
        return

    current_headers = values[0]
    missing = [h for h in DESIRED_HEADERS if h not in current_headers]
    if not missing:
        logger.info("ensure_schema: schema already up to date")
        return

    logger.info(f"ensure_schema: adding missing columns: {missing}")
    data_rows = values[1:]

    # Build old header→index map
    old_idx = {h: i for i, h in enumerate(current_headers)}

    # Rebuild every row against DESIRED_HEADERS
    new_rows = []
    for row in data_rows:
        new_row = []
        for header in DESIRED_HEADERS:
            old_col = old_idx.get(header)
            if old_col is not None and old_col < len(row):
                new_row.append(row[old_col].strip() if isinstance(row[old_col], str) else row[old_col])
            else:
                new_row.append('')
        new_rows.append(new_row)

    all_data = [DESIRED_HEADERS] + new_rows
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=SHEET_NAME,
        valueInputOption='RAW',
        body={'values': all_data},
    ).execute()
    logger.info(f"ensure_schema: rewrote sheet with {len(new_rows)} rows and new headers")


def read_all_rows():
    """Return all data rows as list of dicts keyed by field name."""
    service = get_service()
    sheet_id = _get_sheet_id()
    values = _read_all_values(service, sheet_id)
    if not values:
        return []

    headers = values[0]
    rows = []
    for raw_row in values[1:]:
        padded = raw_row + [''] * (len(headers) - len(raw_row))
        row_dict = {}
        for header, value in zip(headers, padded):
            field = HEADER_TO_FIELD.get(header)
            if field:
                row_dict[field] = value.strip() if isinstance(value, str) else value
        if row_dict.get('serial_number'):
            rows.append(row_dict)
    return rows


def _find_row_index(service, sheet_id):
    """
    Return a dict of {serial_number: row_index_1based} by reading
    the Serial # column dynamically (don't assume a fixed column letter).
    """
    headers = _get_headers(service, sheet_id)
    try:
        serial_col = headers.index('Serial #')
    except ValueError:
        logger.error("ensure_schema must be called before write_row — 'Serial #' column not found")
        return {}

    # Convert 0-based index to A1 column letter (handles up to Z)
    col_letter = chr(ord('A') + serial_col)
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!{col_letter}:{col_letter}",
    ).execute()
    col_values = result.get('values', [])
    index_map = {}
    for i, cell in enumerate(col_values):
        if cell and cell[0].strip():
            index_map[cell[0].strip()] = i + 1  # 1-based row
    return index_map


def _asset_to_row_values(asset_dict, headers):
    """Convert asset dict to ordered list matching the sheet's current header order."""
    return [str(asset_dict.get(HEADER_TO_FIELD.get(h, ''), '') or '') for h in headers]


def write_row(asset_dict):
    """Update the existing row for this asset's serial number."""
    service = get_service()
    sheet_id = _get_sheet_id()
    serial = asset_dict.get('serial_number', '')
    headers = _get_headers(service, sheet_id)
    index_map = _find_row_index(service, sheet_id)

    row_index = index_map.get(serial)
    if row_index is None:
        logger.warning(f"write_row: serial {serial!r} not found in sheet, appending")
        return append_row(asset_dict)

    range_notation = f"{SHEET_NAME}!A{row_index}"
    body = {'values': [_asset_to_row_values(asset_dict, headers)]}
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_notation,
        valueInputOption='RAW',
        body=body,
    ).execute()
    logger.info(f"write_row: updated row {row_index} for serial {serial!r}")


def append_row(asset_dict):
    """Append a new row to the sheet for a brand-new asset."""
    service = get_service()
    sheet_id = _get_sheet_id()
    headers = _get_headers(service, sheet_id)
    body = {'values': [_asset_to_row_values(asset_dict, headers)]}
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{SHEET_NAME}!A1",
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body=body,
    ).execute()
    logger.info(f"append_row: added new row for serial {asset_dict.get('serial_number')!r}")
