# gunicorn_config.py
import multiprocessing

# The socket to bind.
bind = "0.0.0.0:8080"

# Reduced workers — free tier has limited RAM (512MB)
# 4 workers was likely causing memory exhaustion too
workers = 2

# Sync worker
worker_class = 'sync'

# Timeout in seconds — increased for Excel import processing
timeout = 300

# Log level
loglevel = 'info'

# Where to log to
accesslog = '-'  # '-' means log to stdout
errorlog = '-'   # '-' means log to stderr