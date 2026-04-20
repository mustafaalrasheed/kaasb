"""
Kaasb Platform — In-Process Scheduler

Runs periodic jobs across all Gunicorn workers with Redis-based leader
election. Every worker ticks every _TICK_SECONDS and checks if a job is
due; the first worker to acquire the Redis lock runs it, others skip.

Used instead of APScheduler / Celery because:
  * We already have Redis for WS pub/sub and presence — no new infrastructure.
  * Only one daily job today (marketplace_tasks.run_all). Overkill to add a
    separate scheduler service.
  * Cross-worker coordination is handled via Redis SET NX, which is atomic.

Lifecycle:
  * main.py lifespan calls start() on app startup.
  * main.py lifespan calls stop() on app shutdown (graceful drain).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from app.core.database import async_session
from app.services.websocket_manager import _get_redis

logger = logging.getLogger(__name__)

# How often each worker checks if any jobs are due. Lower = faster reaction
# to a missed run after a failure, higher = fewer Redis GETs. 60s is cheap.
_TICK_SECONDS = 60

# Lock TTL — must exceed the longest expected job duration. 30 min is safe
# for marketplace tasks at current scale; revisit if jobs start exceeding 5 min.
_LOCK_TTL_SECONDS = 1800

# Last-run key TTL. Keep for 48h so a missed day (worker offline) is
# detectable: key expires, next worker to tick runs the job immediately.
_LAST_RUN_TTL_SECONDS = 60 * 60 * 48

_shutdown_event: asyncio.Event | None = None
_task: asyncio.Task | None = None

JobRunner = Callable[..., Awaitable[object]]


async def _run_with_lock(job_name: str, runner: JobRunner, interval_hours: int) -> None:
    """
    Run `runner(db)` if the last successful run was ≥ interval_hours ago.
    Only ONE worker in the cluster will execute per interval (Redis SET NX).
    """
    r = await _get_redis()
    lock_key = f"kaasb:sched:lock:{job_name}"
    last_run_key = f"kaasb:sched:last_run:{job_name}"

    last_run_str = await r.get(last_run_key)  # type: ignore[misc]
    if last_run_str:
        try:
            last_run = datetime.fromisoformat(last_run_str)
            if datetime.now(UTC) - last_run < timedelta(hours=interval_hours):
                return
        except ValueError:
            logger.warning("scheduler: invalid last_run timestamp for %s, ignoring", job_name)

    acquired = await r.set(lock_key, "1", ex=_LOCK_TTL_SECONDS, nx=True)  # type: ignore[misc]
    if not acquired:
        return

    try:
        logger.info("scheduler: running job %s", job_name)
        started = datetime.now(UTC)
        async with async_session() as db:
            try:
                await runner(db)
            except Exception:
                await db.rollback()
                raise
        await r.set(last_run_key, started.isoformat(), ex=_LAST_RUN_TTL_SECONDS)  # type: ignore[misc]
        elapsed = (datetime.now(UTC) - started).total_seconds()
        logger.info("scheduler: job %s completed in %.1fs", job_name, elapsed)
    except Exception:
        logger.exception("scheduler: job %s FAILED — will retry on next tick", job_name)
    finally:
        await r.delete(lock_key)  # type: ignore[misc]


async def _scheduler_loop() -> None:
    from app.tasks.marketplace_tasks import run_all as run_marketplace

    assert _shutdown_event is not None
    logger.info("scheduler loop starting (tick=%ds)", _TICK_SECONDS)

    while not _shutdown_event.is_set():
        try:
            await _run_with_lock("marketplace_daily", run_marketplace, interval_hours=24)
        except Exception:
            logger.exception("scheduler: tick errored (continuing)")

        with suppress(TimeoutError):
            await asyncio.wait_for(_shutdown_event.wait(), timeout=_TICK_SECONDS)

    logger.info("scheduler loop stopped")


def start() -> asyncio.Task:
    """Start the scheduler background task. Called from app lifespan startup."""
    global _task, _shutdown_event
    _shutdown_event = asyncio.Event()
    _task = asyncio.create_task(_scheduler_loop(), name="kaasb-scheduler")
    return _task


async def stop() -> None:
    """Signal shutdown and wait for the loop to exit. Called from app lifespan shutdown."""
    if _shutdown_event is not None:
        _shutdown_event.set()
    if _task is not None:
        try:
            await asyncio.wait_for(_task, timeout=10)
        except TimeoutError:
            logger.warning("scheduler: shutdown timed out, cancelling")
            _task.cancel()
