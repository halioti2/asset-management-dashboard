import logging
import os
import sys

from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from flask import Flask, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone

from models import init_db, count_assets
from routes.assets import bp as assets_bp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


FRONTEND_DIST = os.path.join(os.path.dirname(__file__), 'frontend', 'dist')


def create_app():
    app = Flask(__name__)
    CORS(app, origins=['http://localhost:5173', 'http://localhost:3000', 'http://localhost:5001'])

    # Initialize SQLite schema
    init_db()

    # Register blueprints
    app.register_blueprint(assets_bp)

    # Serve built React app for all non-API routes (production only)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        if not os.path.isdir(FRONTEND_DIST):
            from flask import abort
            abort(404)
        full_path = os.path.join(FRONTEND_DIST, path)
        if path and os.path.isfile(full_path):
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, 'index.html')

    # In Flask debug mode the Werkzeug reloader spawns a parent watcher process
    # AND a child worker process, both calling create_app(). We only want to run
    # Sheets API calls and start the scheduler once — in the worker.
    # WERKZEUG_RUN_MAIN is set to 'true' only in the reloader child process.
    is_reloader_parent = (
        os.getenv('FLASK_ENV') == 'development'
        and os.environ.get('WERKZEUG_RUN_MAIN') != 'true'
    )
    if is_reloader_parent:
        logger.info("Reloader parent process — skipping Sheets sync and scheduler")
        return app

    # Ensure sheet has correct headers (adds Email, Phone, Last Updated if missing)
    try:
        from sync.sheets import ensure_schema
        ensure_schema()
    except Exception as e:
        logger.error(f"ensure_schema failed: {e}", exc_info=True)

    # Initial sync: populate DB from Sheets if empty
    _initial_sync()

    # Start background poller — runs immediately on startup, then every 3 minutes.
    # Running immediately ensures any Sheets changes made while the server was
    # down are picked up before serving the first request.
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=_poll_job,
        trigger='interval',
        minutes=3,
        id='sheets_poller',
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    logger.info("Background poller started (runs now, then every 3 minutes)")

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
