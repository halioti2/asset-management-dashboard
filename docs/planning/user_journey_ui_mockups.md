# User Journey & UI Planning: Laptop Checkout/Checkin Management System

## Executive Summary

This document outlines the 5 user journeys for the MVP Asset Management Dashboard. The system uses a single unified admin interface with a 3-section layout:
1. **Action Buttons (Top)** - Check Out, Return, Add Laptop, Lock, Update Notes
2. **Filters & Search (Middle)** - Filter by status, type, category, lease end date
3. **Data Table (Bottom)** - Spreadsheet-like view with selection checkboxes

Each action triggers a form in the top section. After submission, affected records update immediately in the table. Data syncs to Google Sheets within ~3 minutes.

---

## User Journeys (MVP - Asset Management Dashboard)

### Journey 1: Check Out

**Scenario:** Admin checks out a laptop to a student

**Flow:**
```
1. Admin clicks [Check Out] button
2. Form appears in top section with fields:
   - Student Name (text)
   - Email (email)
   - Phone (tel)
   - Duration Needed (dropdown: 1 day, 1 semester)
3. Admin selects laptop from table (bottom section)
4. Laptop details auto-populate:
   - Serial Number (read-only)
   - Model/Type (read-only)
   - Lease Date (read-only, this is the apple lease date not the students return date)
5. Admin clicks [Submit]
6. Record updates in bottom section immediately
7. Google Sheets syncs within 3 minutes
```

**Data Updated:** Student info, checkout date, status → "Checked Out"

---

### Journey 2: Return

**Scenario:** Admin processes laptop return and assesses condition

**Flow:**
```
1. Admin clicks [Return] button
2. Form appears in top section with fields:
   - Notes on condition (textarea - "Excellent", "Good", "Fair", "Damaged", etc.)
   - [MDM Wipe] button (non-functional for MVP - visual only)
3. Admin selects returned laptop from table
4. Laptop details pre-filled (serial, type, borrower info - read-only)
5. Admin enters condition notes
6. Admin clicks [Submit]
7. Record updates:
   - Status → "Returned"
   - Actual Return Date → Today
   - Condition Notes added
8. Record updates in table immediately
```

**Data Updated:** Status, return date, condition notes

---

### Journey 3: Add Laptop

**Scenario:** Admin adds new equipment to inventory

**Flow:**
```
1. Admin clicks [Add Laptop] button
2. Form appears in top section with fields:
   - Label (text - e.g., "MacBook Air #1")
   - Type (dropdown - "MacBook Air", "MacBook Pro", "Dell XPS", etc.)
   - Serial # (text)
   - Category (dropdown - "Laptop", "iPad", "Other")
   - Date Assigned (date picker)
   - Lease End Date (date picker)
   - Setup Notes (textarea, optional)
3. Admin fills all required fields
4. Admin clicks [Submit]
5. New row appears in bottom section with status "Available"
6. Google Sheets syncs new record
```

**Data Added:** New equipment record with all initial details

---

### Journey 4: Lock

**Scenario:** Admin locks/disables a laptop (reported lost or compromised)

**Flow:**
```
1. Admin clicks [Lock] button
2. Form appears in top section with fields:
   - Lock Reason Notes (textarea, optional)
3. Admin selects laptop from table
4. Laptop details pre-filled (read-only)
5. Admin adds notes
6. Admin clicks [Submit]
7. Record updates:
   - Status → "Locked"
   - Lock Reason Notes recorded
   - Timestamp recorded
8. Row highlighted in table to show locked status
```

**Data Updated:** Status → "Locked", lock reason Notes, timestamp

---

### Journey 5: Update Notes

**Scenario:** Admin updates Misc Notes for selected records

**Flow:**
```
1. Admin clicks [Update Misc Notes] button
2. Form appears in top section with field:
   - Misc Notes (textarea - for editing existing notes)
3. Admin selects one or more laptops from table (checkboxes)
4. Admin edits existing notes
5. Admin clicks [Submit]
6. All selected records update:
   - Notes field edited with new content
   - Last Updated timestamp added
7. All selected rows reflect changes immediately in table
```

**Data Updated:** Misc Notes field for selected records, last updated timestamp

---

