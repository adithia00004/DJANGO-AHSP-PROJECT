"""
Gunicorn Configuration for Production Deployment

This configuration file provides optimal settings for running the Django
application with Gunicorn in production environments.

Usage:
    gunicorn -c gunicorn.conf.py config.wsgi:application

Documentation:
    https://docs.gunicorn.org/en/stable/settings.html
"""

import os
import multiprocessing

# ============================================================================
# Server Socket
# ============================================================================

# Bind to all interfaces on port 8000
# In production, this should be behind Nginx/Apache reverse proxy
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')

# Backlog of pending connections
# The maximum number of pending connections
backlog = 2048


# ============================================================================
# Worker Processes
# ============================================================================

# Number of worker processes
# Rule of thumb: (2 x $num_cores) + 1
# For CPU-bound apps: num_cores
# For I/O-bound apps (most Django apps): 2-4 x num_cores
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# Worker class
# sync: Default, good for most Django apps
# gevent/eventlet: For async/streaming apps (requires gevent/eventlet)
# uvicorn: For ASGI apps (Django Channels)
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'sync')

# Worker connections (for async workers)
# Only relevant for gevent/eventlet/tornado worker classes
worker_connections = 1000

# Max requests per worker before restart
# Prevents memory leaks from accumulating
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 1000))

# Randomize max_requests to prevent all workers restarting at once
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', 50))

# Worker timeout (seconds)
# If a worker doesn't respond within this time, it's killed and restarted
# Increase for long-running requests (exports, batch operations)
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))

# Graceful timeout (seconds)
# Time to wait for workers to finish serving requests during graceful shutdown
graceful_timeout = 30

# Keep-alive timeout (seconds)
# Seconds to wait for requests on a Keep-Alive connection
keepalive = 2


# ============================================================================
# Logging
# ============================================================================

# Access log file
# '-' means log to stdout (recommended for containerized environments)
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', 'logs/gunicorn-access.log')

# Error log file
# '-' means log to stderr (recommended for containerized environments)
errorlog = os.environ.get('GUNICORN_ERROR_LOG', 'logs/gunicorn-error.log')

# Log level
# debug, info, warning, error, critical
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')

# Access log format
# h: remote address
# l: '-'
# u: user name
# t: date of the request
# r: status line (e.g. GET / HTTP/1.1)
# s: status
# b: response length
# f: referer
# a: user agent
# T: request time in seconds
# D: request time in microseconds
# L: request time in decimal seconds
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# Capture output from stdout/stderr
# Useful for debugging, but may impact performance
capture_output = False


# ============================================================================
# Process Naming
# ============================================================================

# Name of the gunicorn process
# Useful for process monitoring
proc_name = os.environ.get('GUNICORN_PROC_NAME', 'ahsp-gunicorn')


# ============================================================================
# Server Mechanics
# ============================================================================

# Daemonize the process
# Set to True for background execution
# Set to False for Docker/systemd (they handle daemonization)
daemon = False

# PID file location
pidfile = os.environ.get('GUNICORN_PID_FILE', 'logs/gunicorn.pid')

# User to run workers as (Unix only)
# Requires running gunicorn as root
# user = 'www-data'
# group = 'www-data'

# Directory to change to before loading the app
# chdir = '/path/to/project'

# Preload application code before worker processes are forked
# Faster worker spawn, but less memory isolation
# Set to True for production with stable code
preload_app = os.environ.get('GUNICORN_PRELOAD', 'False').lower() == 'true'


# ============================================================================
# Server Hooks
# ============================================================================

def on_starting(server):
    """
    Called just before the master process is initialized.
    """
    server.log.info("Starting Gunicorn server...")


def on_reload(server):
    """
    Called to recycle workers during a reload via SIGHUP.
    """
    server.log.info("Reloading Gunicorn server...")


def when_ready(server):
    """
    Called just after the server is started.
    """
    server.log.info(f"Gunicorn server is ready. Listening on {bind}")
    server.log.info(f"Workers: {workers}, Timeout: {timeout}s")


def pre_fork(server, worker):
    """
    Called just before a worker is forked.
    """
    pass


def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    """
    server.log.info(f"Worker spawned (pid: {worker.pid})")


def pre_exec(server):
    """
    Called just before a new master process is forked.
    """
    server.log.info("Forked child, re-executing.")


def worker_int(worker):
    """
    Called when a worker receives the INT or QUIT signal.
    """
    worker.log.info(f"Worker received INT or QUIT signal (pid: {worker.pid})")


def worker_abort(worker):
    """
    Called when a worker is aborted (timeout).
    """
    worker.log.warning(f"Worker timeout, aborting (pid: {worker.pid})")


def pre_request(worker, req):
    """
    Called just before a worker processes a request.
    """
    # Log slow requests
    # worker.log.debug(f"{req.method} {req.path}")
    pass


def post_request(worker, req, environ, resp):
    """
    Called after a worker processes a request.
    """
    pass


def child_exit(server, worker):
    """
    Called just after a worker has been exited.
    """
    server.log.info(f"Worker exited (pid: {worker.pid})")


def worker_exit(server, worker):
    """
    Called just after a worker has been exited.
    """
    pass


def nworkers_changed(server, new_value, old_value):
    """
    Called just after num_workers has been changed.
    """
    server.log.info(f"Workers changed from {old_value} to {new_value}")


def on_exit(server):
    """
    Called just before exiting Gunicorn.
    """
    server.log.info("Shutting down Gunicorn server...")


# ============================================================================
# SSL Configuration (if needed)
# ============================================================================

# Uncomment and configure if terminating SSL at Gunicorn level
# (Usually handled by Nginx/Apache in production)

# keyfile = '/path/to/ssl/key.pem'
# certfile = '/path/to/ssl/cert.pem'
# ca_certs = '/path/to/ssl/ca.pem'
# ssl_version = 'TLSv1_2'
# cert_reqs = 0  # ssl.CERT_NONE
# ciphers = 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256'


# ============================================================================
# Development vs Production Recommendations
# ============================================================================

"""
DEVELOPMENT:
    workers = 2
    timeout = 30
    loglevel = 'debug'
    reload = True
    accesslog = '-'
    errorlog = '-'

STAGING:
    workers = (2 * cores) + 1
    timeout = 60
    loglevel = 'info'
    reload = False
    accesslog = 'logs/gunicorn-access.log'
    errorlog = 'logs/gunicorn-error.log'

PRODUCTION:
    workers = (2 * cores) + 1
    timeout = 120
    loglevel = 'warning'
    reload = False
    accesslog = 'logs/gunicorn-access.log'
    errorlog = 'logs/gunicorn-error.log'
    max_requests = 1000
    max_requests_jitter = 50
    preload_app = True
"""
