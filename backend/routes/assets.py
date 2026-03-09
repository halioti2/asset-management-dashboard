from datetime import date
from flask import Blueprint, request, jsonify
from models import (
    get_all_assets, get_asset_by_id, insert_asset, update_asset,
    derive_status,
)
from sync.sheets import write_row, append_row
from sync.poller import update_cache_for_row

bp = Blueprint('assets', __name__, url_prefix='/api/assets')


def _error(msg, code=400):
    return jsonify({'error': msg}), code


def _queue_sheets_write(asset):
    """Fire-and-forget sheets write; log errors but don't fail the request.
    Updates the poll cache on success so the poller doesn't re-push stale data."""
    try:
        write_row(asset)
        update_cache_for_row(asset)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"sheets write failed for {asset.get('serial_number')}: {e}")


def _queue_sheets_append(asset):
    try:
        append_row(asset)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"sheets append failed for {asset.get('serial_number')}: {e}")


def _apply_filters(assets, params):
    status = params.get('status')
    assigned_to = params.get('assigned_to')
    asset_type = params.get('type')
    before = params.get('lease_end_date_before')
    after = params.get('lease_end_date_after')

    result = assets
    if status:
        result = [a for a in result if a['status'] == status]
    if assigned_to:
        result = [a for a in result if (a.get('assigned_to') or '').lower() == assigned_to.lower()]
    if asset_type:
        result = [a for a in result if (a.get('type') or '').lower() == asset_type.lower()]
    if before:
        result = [a for a in result if a.get('lease_end_date') and a['lease_end_date'] <= before]
    if after:
        result = [a for a in result if a.get('lease_end_date') and a['lease_end_date'] >= after]
    return result


# ── GET /api/assets ────────────────────────────────────────────────────────────

@bp.route('', methods=['GET'])
def list_assets():
    assets = get_all_assets()
    filtered = _apply_filters(assets, request.args)
    return jsonify(filtered)


# ── POST /api/assets  (J3 — Add Laptop) ───────────────────────────────────────

@bp.route('', methods=['POST'])
def add_asset():
    body = request.get_json(force=True) or {}
    required = ['type', 'serial_number', 'category']
    missing = [f for f in required if not body.get(f, '').strip()]
    if missing:
        return _error(f"Missing required fields: {', '.join(missing)}")

    asset = insert_asset(body)
    _queue_sheets_append(asset)
    return jsonify(asset), 201


# ── PATCH /api/assets/:id/checkout  (J1) ──────────────────────────────────────

@bp.route('/<int:asset_id>/checkout', methods=['PATCH'])
def checkout_asset(asset_id):
    asset = get_asset_by_id(asset_id)
    if not asset:
        return _error('Asset not found', 404)
    if derive_status(asset) != 'Not Assigned':
        return _error(f"Asset is {derive_status(asset)}, not available for checkout", 409)

    body = request.get_json(force=True) or {}
    required = ['assigned_to', 'email', 'phone']
    missing = [f for f in required if not body.get(f, '').strip()]
    if missing:
        return _error(f"Missing required fields: {', '.join(missing)}")

    updated = update_asset(asset_id, {
        'assigned_to': body['assigned_to'].strip(),
        'email': body['email'].strip(),
        'phone': body['phone'].strip(),
    })
    _queue_sheets_write(updated)
    return jsonify(updated)


# ── PATCH /api/assets/:id/return  (J2) ────────────────────────────────────────

@bp.route('/<int:asset_id>/return', methods=['PATCH'])
def return_asset(asset_id):
    asset = get_asset_by_id(asset_id)
    if not asset:
        return _error('Asset not found', 404)
    if derive_status(asset) != 'Checked Out':
        return _error(f"Asset is {derive_status(asset)}, not currently checked out", 409)

    body = request.get_json(force=True) or {}
    notes_addition = body.get('notes', '').strip()

    existing_notes = asset.get('notes', '') or ''
    if notes_addition:
        separator = '\n' if existing_notes else ''
        new_notes = f"{existing_notes}{separator}{notes_addition}"
    else:
        new_notes = existing_notes

    today = date.today().isoformat()
    updated = update_asset(asset_id, {
        'notes': new_notes,
        'returned': today,
    })
    _queue_sheets_write(updated)

    # Create a fresh Not Assigned record for the same device
    new_asset = insert_asset({
        'label': asset.get('label', ''),
        'type': asset.get('type', ''),
        'serial_number': asset.get('serial_number', ''),
        'category': asset.get('category', ''),
        'date_assigned': asset.get('date_assigned', ''),
        'lease_end_date': asset.get('lease_end_date', ''),
    })
    _queue_sheets_append(new_asset)

    return jsonify(updated)


# ── PATCH /api/assets/:id/lock  (J4) ──────────────────────────────────────────

@bp.route('/<int:asset_id>/lock', methods=['PATCH'])
def lock_asset(asset_id):
    asset = get_asset_by_id(asset_id)
    if not asset:
        return _error('Asset not found', 404)

    body = request.get_json(force=True) or {}
    reason = body.get('notes', '').strip()

    from datetime import datetime
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    lock_entry = f"[locked] {timestamp}" + (f": {reason}" if reason else "")

    existing_notes = asset.get('notes', '') or ''
    separator = '\n' if existing_notes else ''
    new_notes = f"{existing_notes}{separator}{lock_entry}"

    updated = update_asset(asset_id, {'notes': new_notes})
    _queue_sheets_write(updated)
    return jsonify(updated)


# ── POST /api/sync ─────────────────────────────────────────────────────────────

@bp.route('/sync', methods=['POST'])
def sync_from_sheets():
    try:
        from sync.poller import force_sync_from_sheets
        count = force_sync_from_sheets()
        return jsonify({'synced': count})
    except Exception as e:
        return _error(str(e), 500)


# ── PATCH /api/assets/notes  (J5 — bulk) ──────────────────────────────────────

@bp.route('/notes', methods=['PATCH'])
def bulk_update_notes():
    body = request.get_json(force=True) or {}
    ids = body.get('ids', [])
    notes = body.get('notes', '')

    if not ids:
        return _error("'ids' is required and must be a non-empty list")
    if notes is None:
        return _error("'notes' is required")

    updated = []
    for asset_id in ids:
        asset = get_asset_by_id(asset_id)
        if not asset:
            continue
        asset = update_asset(asset_id, {'notes': notes})
        _queue_sheets_write(asset)
        updated.append(asset)

    return jsonify(updated)
