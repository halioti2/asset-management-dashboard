import logging
import os
import sys

from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

from models import init_db, count_assets
from routes.assets import bp as assets_bp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    CORS(app, origins=['http://localhost:5173', 'http://localhost:3000', 'http://localhost:5001'])

    # Initialize SQLite schema
    init_db()

    # Register blueprints
    app.register_blueprint(assets_bp)

    # Ensure sheet has correct headers (adds Email, Phone, Last Updated if missing)
    try:
        from sync.sheets import ensure_schema
        ensure_schema()
    except Exception as e:
        logger.error(f"ensure_schema failed: {e}", exc_info=True)

    # Initial sync: populate DB from Sheets if empty
    _initial_sync()

    # Start background poller (every 3 minutes)
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=_poll_job,
        trigger='interval',
        minutes=3,
        id='sheets_poller',
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background poller started (3-minute interval)")

    return app


def _initial_sync():
    """On startup: if DB is empty, pull all rows from Sheets."""
    try:
        if count_assets() == 0:
            logger.info("DB is empty — running initial sync from Google Sheets...")
            from sync.sheets import read_all_rows
            from models import upsert_asset_from_sheets
            rows = read_all_rows()
            for row in rows:
                if row.get('serial_number'):
                    upsert_asset_from_sheets(row)
            logger.info(f"Initial sync complete: {len(rows)} rows imported")
        else:
            logger.info(f"DB already has {count_assets()} assets, skipping initial sync")
    except Exception as e:
        logger.error(f"Initial sync failed: {e}", exc_info=True)


def _poll_job():
    from sync.poller import run_poll
    run_poll()


if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development')
