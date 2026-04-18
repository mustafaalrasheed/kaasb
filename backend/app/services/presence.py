"""
Kaasb Platform - Presence Service

Tracks "user is online right now" across all workers via Redis. Each WS
connect/disconnect updates a Redis SET; any worker (or REST endpoint) can
query it without talking to the other workers.

Design choices:
  * Redis SET (``kaasb:presence:online``) is the source of truth for live
    presence. A set is O(1) to add/remove/check, and doesn't need the per-user
    TTL + counter machinery that a hash would require.
  * Per-user counter (``kaasb:presence:conns:{user_id}``) so a user with
    multiple tabs / devices only shows offline once ALL of them disconnect.
  * ``users.last_seen_at`` (DB) is written on the final disconnect — it's
    the durable fallback for showing "Last seen 10m ago" after the user
    has fully gone offline. Not written on every connect/disconnect
    to avoid write amplification.
  * In-memory fallback when Redis is unreachable (dev / single-worker).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import update

from app.core.database import async_session
from app.models.user import User
from app.services.websocket_manager import _get_redis

logger = logging.getLogger(__name__)

_ONLINE_SET = "kaasb:presence:online"
_CONN_COUNT_PREFIX = "kaasb:presence:conns:"

# In-memory fallback — only used when Redis is unreachable. Per-worker, so
# presence across workers relies on Redis. That is fine for dev/single-worker.
_fallback_online: dict[str, int] = {}


async def _incr_fallback(uid: str) -> int:
    _fallback_online[uid] = _fallback_online.get(uid, 0) + 1
    return _fallback_online[uid]


async def _decr_fallback(uid: str) -> int:
    n = _fallback_online.get(uid, 0) - 1
    if n <= 0:
        _fallback_online.pop(uid, None)
        return 0
    _fallback_online[uid] = n
    return n


async def mark_online(user_id: uuid.UUID) -> None:
    """
    Register a new WS connection for this user. Increments the connection
    counter; on the first connection (0 → 1) the user is added to the
    global online set.
    """
    uid = str(user_id)
    try:
        r = await _get_redis()
        # INCR is atomic. We read the result to know if this is the first conn.
        # redis-py types async returns as T | Awaitable[T] because the same
        # interface covers both sync and async clients — hence the ignores.
        count = await r.incr(f"{_CONN_COUNT_PREFIX}{uid}")  # type: ignore[misc]
        if count == 1:
            await r.sadd(_ONLINE_SET, uid)  # type: ignore[misc]
    except Exception as e:
        logger.warning("presence: redis mark_online failed (%s) — using fallback", e)
        await _incr_fallback(uid)


async def mark_offline(user_id: uuid.UUID) -> bool:
    """
    Decrement the connection counter. Returns True if the user is now fully
    offline (no remaining connections), False if they still have other tabs /
    devices open. Also writes ``users.last_seen_at`` on the final disconnect.
    """
    uid = str(user_id)
    now_fully_offline = False
    try:
        r = await _get_redis()
        count = await r.decr(f"{_CONN_COUNT_PREFIX}{uid}")  # type: ignore[misc]
        if count <= 0:
            await r.delete(f"{_CONN_COUNT_PREFIX}{uid}")  # type: ignore[misc]
            await r.srem(_ONLINE_SET, uid)  # type: ignore[misc]
            now_fully_offline = True
    except Exception as e:
        logger.warning("presence: redis mark_offline failed (%s) — using fallback", e)
        remaining = await _decr_fallback(uid)
        now_fully_offline = remaining == 0

    if now_fully_offline:
        await _persist_last_seen(user_id)
    return now_fully_offline


async def is_online(user_id: uuid.UUID) -> bool:
    """Check if any worker has an active WS for this user."""
    uid = str(user_id)
    try:
        r = await _get_redis()
        return bool(await r.sismember(_ONLINE_SET, uid))  # type: ignore[misc]
    except Exception:
        return uid in _fallback_online


async def get_online(user_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Batch lookup — returns the subset of the input that is currently online."""
    if not user_ids:
        return set()
    try:
        r = await _get_redis()
        # SMISMEMBER returns a list of 0/1 in the same order as args.
        uids = [str(u) for u in user_ids]
        flags = await r.smismember(_ONLINE_SET, uids)  # type: ignore[misc]
        return {user_ids[i] for i, f in enumerate(flags) if f}
    except Exception:
        return {u for u in user_ids if str(u) in _fallback_online}


async def _persist_last_seen(user_id: uuid.UUID) -> None:
    """Update users.last_seen_at on final disconnect. Swallows errors."""
    try:
        async with async_session() as db:
            try:
                await db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(last_seen_at=datetime.now(UTC))
                )
                await db.commit()
            except Exception:
                await db.rollback()
                raise
    except Exception:
        logger.exception("presence: failed to persist last_seen_at for %s", user_id)
