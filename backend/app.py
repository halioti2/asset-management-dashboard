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

    # In Flask debug mode, start the scheduler inline (no gunicorn fork risk).
    # In production under gunicorn, the scheduler is started by gunicorn.conf.py
    # post_fork hook after the worker process is forked, avoiding the
    # fork-after-threading deadlock that occurs when a background thread is
    # running in the master process at fork time.
    if os.getenv('FLASK_ENV') == 'development':
        is_reloader_parent = os.environ.get('WERKZEUG_RUN_MAIN') != 'true'
        if not is_reloader_parent:
            start_scheduler()

    return app


def start_scheduler():
    """Start the background poller scheduler. Called after fork in production
    (via gunicorn.conf.py post_fork) or inline in development."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=_startup_job,
        trigger='interval',
        minutes=3,
        id='sheets_poller',
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    logger.info("Background poller started (runs now, then every 3 minutes)")


def _startup_job():
    """Run on startup and every 3 minutes. On first run, seeds DB if empty."""
    try:
        if count_assets() == 0:
            logger.info("DB is empty — running initial sync from Google Sheets...")
            from sync.poller import force_sync_from_sheets
            count = force_sync_from_sheets()
            logger.info(f"Initial sync complete: {count} rows imported")
        else:
            from sync.poller import run_poll
            run_poll()
    except Exception as e:
        logger.error(f"Startup job failed: {e}", exc_info=True)


if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development')
