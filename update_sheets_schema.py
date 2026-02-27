#!/usr/bin/env python3
"""
Update Google Sheets schema:
1. Add Email column (after Assigned To)
2. Add Phone column (after Email)
3. Add Last Updated column (at end)
4. Clean trailing spaces from Type column
"""

import os
import json
import sys
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = "1R2Blpr0A_9bgcfXx9EViwmDHy3Z41ZhtKTNiOKbtX5M"
SHEET_NAME = "Distribution Tracker"

def get_credentials():
    """Load service account credentials from .env"""
    try:
        creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            raise ValueError("GOOGLE_SHEETS_CREDENTIALS not found in .env")
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return credentials
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")
        sys.exit(1)

def read_all_data(service):
    """Read all data from sheet"""
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}"
    ).execute()
    return result.get('values', [])

def update_sheet(service, values):
    """Write updated data back to sheet"""
    body = {'values': values}
    result = service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}",
        valueInputOption='RAW',
        body=body
    ).execute()
    return result

def main():
    print("🔄 Updating Google Sheets Schema\n")

    # Get credentials and service
    credentials = get_credentials()
    service = build('sheets', 'v4', credentials=credentials)

    # Read current data
    print("📖 Reading current sheet data...")
    values = read_all_data(service)

    if not values:
        print("❌ No data found")
        sys.exit(1)

    headers = values[0]
    data_rows = values[1:]

    print(f"✅ Read {len(data_rows)} data rows")
    print(f"   Current columns: {headers}\n")

    # Define new header structure
    # Original: Label, Type, Assigned To, Serial #, Date Assigned, Category, Lease End Date, Notes, Returned
    # New: Label, Type, Assigned To, Email, Phone, Serial #, Date Assigned, Category, Lease End Date, Notes, Returned, Last Updated

    new_headers = [
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
        'Last Updated'
    ]

    print("🔧 Making changes:")

    # 1. Build new data rows with new columns
    new_rows = []
    for row_idx, row in enumerate(data_rows):
        # Pad row to have all original columns
        while len(row) < len(headers):
            row.append('')

        # Map old data to new structure
        # Old column positions
        label_idx = headers.index('Label') if 'Label' in headers else 0
        type_idx = headers.index('Type') if 'Type' in headers else 1
        assigned_to_idx = headers.index('Assigned To') if 'Assigned To' in headers else 2
        serial_idx = headers.index('Serial #') if 'Serial #' in headers else 3
        date_assigned_idx = headers.index('Date Assigned') if 'Date Assigned' in headers else 4
        category_idx = headers.index('Category') if 'Category' in headers else 5
        lease_end_idx = headers.index('Lease End Date') if 'Lease End Date' in headers else 6
        notes_idx = headers.index('Notes') if 'Notes' in headers else 7
        returned_idx = headers.index('Returned') if 'Returned' in headers else 8

        # Clean Type field (remove trailing spaces)
        type_val = row[type_idx].strip() if type_idx < len(row) else ''

        new_row = [
            row[label_idx] if label_idx < len(row) else '',  # Label
            type_val,  # Type (cleaned)
            row[assigned_to_idx] if assigned_to_idx < len(row) else '',  # Assigned To
            '',  # Email (new, empty)
            '',  # Phone (new, empty)
            row[serial_idx] if serial_idx < len(row) else '',  # Serial #
            row[date_assigned_idx] if date_assigned_idx < len(row) else '',  # Date Assigned
            row[category_idx] if category_idx < len(row) else '',  # Category
            row[lease_end_idx] if lease_end_idx < len(row) else '',  # Lease End Date
            row[notes_idx] if notes_idx < len(row) else '',  # Notes
            row[returned_idx] if returned_idx < len(row) else '',  # Returned
            ''  # Last Updated (new, empty)
        ]
        new_rows.append(new_row)

    print(f"   ✅ Added Email column")
    print(f"   ✅ Added Phone column")
    print(f"   ✅ Added Last Updated column")
    print(f"   ✅ Cleaned trailing spaces from Type column")

    # 2. Write updated data
    print(f"\n📝 Writing {len(new_rows)} rows to sheet...")
    all_data = [new_headers] + new_rows
    result = update_sheet(service, all_data)

    print(f"✅ Updated {result.get('updatedRows')} rows")

    print(f"\n📊 New column structure:")
    for i, col in enumerate(new_headers, 1):
        print(f"   {i}. {col}")

    print("\n" + "="*60)
    print("✅ Schema update completed successfully!")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
