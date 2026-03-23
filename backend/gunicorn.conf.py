def post_fork(server, worker):
    """Start the background scheduler in each worker after forking.
    Must NOT run in the master process — starting a background thread before
    fork and then forking causes the worker to inherit locked thread state,
    deadlocking gunicorn workers on every deploy."""
    from app import start_scheduler
    start_scheduler()
