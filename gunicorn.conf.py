"""
Gunicorn configuration file for production FastAPI deployment.

This configuration follows best practices for running FastAPI with Gunicorn and Uvicorn workers.
Designed to work with the Phase 4 scaling architecture.

Usage:
    gunicorn app.main:create_app --factory -c gunicorn.conf.py
"""

import multiprocessing
import os

# Server socket
bind = os.getenv("BIND", "0.0.0.0:8000")

# Worker processes
# Auto-detect based on CPU cores if not specified
# Formula: (2 * CPU cores) + 1 for I/O bound workloads
workers_env = os.getenv("WORKERS", "0")
workers = (
    int(workers_env)
    if int(workers_env) > 0
    else (multiprocessing.cpu_count() * 2) + 1
)

# Worker class (use Uvicorn for async FastAPI)
worker_class = "uvicorn.workers.UvicornWorker"

# Worker timeout (seconds)
# Increase for long-running operations (e.g., LLM API calls)
timeout = int(os.getenv("WORKER_TIMEOUT", "30"))

# Graceful timeout (seconds)
# Time to allow workers to finish current requests during shutdown
graceful_timeout = int(os.getenv("GRACEFUL_TIMEOUT", "30"))

# Keep-alive timeout
keepalive = int(os.getenv("KEEPALIVE", "5"))

# Worker recycling (prevents memory leaks)
# Restart worker after this many requests
max_requests = int(os.getenv("MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("MAX_REQUESTS_JITTER", "100"))

# Preload app (faster worker spawn, but can't reload without restart)
# Set to False if you want to use kill -HUP for zero-downtime reloads
preload_app = os.getenv("PRELOAD_APP", "True").lower() == "true"

# Logging
accesslog = os.getenv("ACCESS_LOG", "-")  # stdout
errorlog = os.getenv("ERROR_LOG", "-")    # stderr
loglevel = os.getenv("LOG_LEVEL", "info").lower()

# Access log format with request ID
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" %(L)s %(p)s'
)

# Process naming
proc_name = os.getenv("PROC_NAME", "fastapi-backend")

# Daemon mode (set to False for Docker containers)
daemon = False

# PID file location (for process management)
pidfile = os.getenv("PID_FILE", None)

# Worker temporary directory
worker_tmp_dir = os.getenv("WORKER_TMP_DIR", "/dev/shm" if os.path.exists("/dev/shm") else None)

# Server hooks for custom behavior
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info(f"Starting Gunicorn with {workers} workers")


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Gunicorn workers")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"Gunicorn ready. Workers: {workers}, Timeout: {timeout}s")


def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"Worker {worker.pid} received SIGINT/SIGQUIT")


def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f"Worker {worker.pid} aborted (timeout or error)")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    # Hook for pre-fork initialization if needed
    server.log.debug(f"About to fork worker {worker.pid}")


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")


def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process")


def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.info(f"Worker exited (pid: {worker.pid})")
