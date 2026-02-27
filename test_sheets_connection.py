#!/usr/bin/env python3
"""
Test script to verify Google Sheets connection and read current sheet format
"""

import os
import json
import sys
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Load environment variables from .env
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

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

def get_spreadsheet_id():
    """Get spreadsheet ID from command line arg or environment variable"""
    # Try command line argument first
    if len(sys.argv) > 1:
        spreadsheet_id = sys.argv[1].strip()
    # Then try environment variable
    elif os.getenv('GOOGLE_SHEET_ID'):
        spreadsheet_id = os.getenv('GOOGLE_SHEET_ID').strip()
    # Finally try interactive input
    else:
        try:
            spreadsheet_id = input("Enter your Google Sheet ID (from the URL): ").strip()
        except EOFError:
            print("❌ Spreadsheet ID required. Provide it as:")
            print("   python test_sheets_connection.py <SHEET_ID>")
            print("   or set GOOGLE_SHEET_ID environment variable")
            sys.exit(1)

    if not spreadsheet_id:
        print("❌ Spreadsheet ID required")
        sys.exit(1)
    return spreadsheet_id

def read_sheet(service, spreadsheet_id):
    """Read the first sheet and display its structure"""
    try:
        # Get sheet metadata
        sheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet.get('sheets', [])

        if not sheets:
            print("❌ No sheets found in spreadsheet")
            sys.exit(1)

        first_sheet = sheets[0]
        sheet_name = first_sheet['properties']['title']
        print(f"\n📋 Sheet Name: {sheet_name}")

        # Read all data from first sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}"
        ).execute()

        values = result.get('values', [])

        if not values:
            print("❌ No data found in sheet")
            sys.exit(1)

        # Parse header and data
        headers = values[0]
        data_rows = values[1:]

        print(f"\n✅ Successfully connected to Google Sheets!")
        print(f"\n📊 Sheet Structure:")
        print(f"   Total rows: {len(values)} (1 header + {len(data_rows)} data rows)")
        print(f"   Total columns: {len(headers)}")

        print(f"\n📝 Column Headers:")
        for i, header in enumerate(headers, 1):
            print(f"   {i}. {header}")

        # Display first 3 rows of data
        print(f"\n📄 Sample Data (first 3 rows):")
        for row_num, row in enumerate(data_rows[:3], 1):
            print(f"\n   Row {row_num}:")
            for col_idx, (header, value) in enumerate(zip(headers, row)):
                value_display = value[:50] + "..." if len(value) > 50 else value
                print(f"      {header}: {value_display}")

        # Validate expected columns
        print(f"\n🔍 Column Validation:")
        expected_columns = {
            'Label': False,
            'Type': False,
            'Assigned To': False,
            'Serial #': False,
            'Date Assigned': False,
            'Category': False,
            'Lease End Date': False,
            'Notes': False,
            'Returned': False
        }

        for header in headers:
            if header in expected_columns:
                expected_columns[header] = True

        for col_name, found in expected_columns.items():
            status = "✅" if found else "⚠️"
            print(f"   {status} {col_name}")

        missing = [col for col, found in expected_columns.items() if not found]
        if missing:
            print(f"\n⚠️ Missing columns: {', '.join(missing)}")
        else:
            print(f"\n✅ All expected columns found!")

        # Additional columns not in expected list
        unexpected = [h for h in headers if h not in expected_columns]
        if unexpected:
            print(f"\n📌 Additional columns (for notes/future use): {', '.join(unexpected)}")

        return True

    except Exception as e:
        print(f"❌ Error reading sheet: {e}")
        sys.exit(1)

def main():
    print("🔐 Google Sheets Connection Test\n")

    # Get credentials
    print("Loading service account credentials...")
    credentials = get_credentials()
    print("✅ Credentials loaded successfully")

    # Get spreadsheet ID from user
    print("\nYou can find your Sheet ID in the URL:")
    print("https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
    spreadsheet_id = get_spreadsheet_id()

    # Build service
    service = build('sheets', 'v4', credentials=credentials)

    # Read sheet
    read_sheet(service, spreadsheet_id)

    print("\n" + "="*60)
    print("✅ Test completed successfully!")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
