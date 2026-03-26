"""
Kaasb Platform — Gunicorn Production Configuration
Tuned for Hetzner CX22 (2 vCPU, 4 GB RAM) running inside Docker.

Worker formula:  2 * CPU + 1  (CPU-bound async tasks use fewer workers than sync)
We cap at 5 to stay within 4 GB RAM; override via WEB_CONCURRENCY env var.
"""

import multiprocessing
import os

# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------
_cpu = multiprocessing.cpu_count()
workers = int(os.getenv("WEB_CONCURRENCY", min(_cpu * 2 + 1, 5)))
worker_class = "uvicorn.workers.UvicornWorker"

# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------
bind = "0.0.0.0:8000"

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
timeout = 60           # Kill worker if it doesn't respond in 60s
graceful_timeout = 30  # Give workers 30s to finish in-flight requests on SIGTERM
keepalive = 5          # Reuse connections for 5s (reduces TCP overhead)

# ---------------------------------------------------------------------------
# Memory-leak prevention
# ---------------------------------------------------------------------------
max_requests = 1000         # Restart worker after N requests
max_requests_jitter = 100   # ±100 jitter prevents thundering herd restarts

# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
preload_app = True          # Load app once in master — saves RAM via copy-on-write
worker_tmp_dir = "/dev/shm" # Heartbeat files in RAM FS (avoids slow disk I/O)

# ---------------------------------------------------------------------------
# Logging  (JSON for production — parsed by log aggregators)
# ---------------------------------------------------------------------------
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = (
    '{"time":"%(t)s","method":"%(m)s","path":"%(U)s%(q)s",'
    '"status":%(s)s,"bytes":%(b)s,"duration_s":%(L)s,"ip":"%(h)s","referer":"%(f)s"}'
)
