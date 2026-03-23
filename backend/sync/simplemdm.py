"""SimpleMDM API client — lock and wipe devices."""

import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

API_BASE = 'https://api.simplemdm.com/api/v1'


def _auth():
    key = os.getenv('SIMPLEMDM_API_KEY', '').strip()
    if not key:
        raise ValueError('SIMPLEMDM_API_KEY not set in .env')
    return (key, '')


def lookup_device(serial_number):
    """Search SimpleMDM for a device by serial number.
    Returns {id, name, serial_number, status, model} or None."""
    resp = requests.get(
        f'{API_BASE}/devices',
        auth=_auth(),
        params={'search': serial_number},
    )
    if resp.status_code == 401:
        raise ValueError('Invalid SimpleMDM API key')
    resp.raise_for_status()

    for device in resp.json().get('data', []):
        attrs = device.get('attributes', {})
        if attrs.get('serial_number', '').upper() == serial_number.upper():
            return {
                'id': device['id'],
                'name': attrs.get('name', ''),
                'serial_number': attrs['serial_number'],
                'status': attrs.get('status', ''),
                'model': attrs.get('model_name', ''),
            }
    return None


def lock_device(device_id, pin=None, message=None):
    """Send lock command to a device. Returns success dict or raises."""
    payload = {}
    if pin:
        payload['pin'] = pin
    if message:
        payload['message'] = message

    resp = requests.post(
        f'{API_BASE}/devices/{device_id}/lock',
        auth=_auth(),
        json=payload,
    )
    if resp.status_code == 401:
        raise ValueError('Invalid SimpleMDM API key')
    if resp.status_code not in (200, 202, 204):
        raise RuntimeError(f'Lock failed (HTTP {resp.status_code}): {resp.text}')
    return {'success': True}


def wipe_device(device_id):
    """Send wipe command to a device. Returns success dict or raises."""
    resp = requests.post(
        f'{API_BASE}/devices/{device_id}/wipe',
        auth=_auth(),
    )
    if resp.status_code == 401:
        raise ValueError('Invalid SimpleMDM API key')
    if resp.status_code not in (200, 202, 204):
        raise RuntimeError(f'Wipe failed (HTTP {resp.status_code}): {resp.text}')
    return {'success': True}
