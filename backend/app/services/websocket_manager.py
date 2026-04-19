"""
Kaasb Platform - WebSocket Connection Manager
Manages active WebSocket connections with Redis pub/sub for multi-worker support.

Architecture:
  - Each Gunicorn worker keeps its own in-process _connections dict.
  - send_to_user() both:
      (a) delivers directly to local connections (same worker, O(1))
      (b) publishes to Redis channel kaasb:ws:{user_id} (other workers)
  - Each worker starts a Redis subscriber coroutine (started in main.py lifespan)
    that listens for published events and delivers to its local connections.
  - WS tickets are stored in Redis so any worker can redeem them.

WS Ticket flow (solves httpOnly cookie problem):
  1. Frontend calls POST /auth/ws-ticket (authenticated via cookie) → gets 60s ticket
  2. Frontend opens WebSocket with ?ticket=<ticket>
  3. ws.py redeems ticket (single-use, stored in Redis) and registers the connection
"""

import asyncio
import json
import logging
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Redis channel prefix for WebSocket delivery
_WS_CHANNEL_PREFIX = "kaasb:ws:"
# Redis key prefix + TTL for WS tickets
_TICKET_PREFIX = "kaasb:ws_ticket:"
_TICKET_TTL_SECONDS = 60

# Unique per worker process — used to suppress self-echo from Redis pub/sub.
# When worker A publishes to Redis, ALL subscribers (including A itself) receive
# the message. We tag outgoing envelopes with this ID so the subscriber can
# skip messages it already delivered locally via _deliver_local.
_WORKER_ID = str(os.getpid())

_redis: aioredis.Redis | None = None


def _get_settings():
    return get_settings()


async def _get_redis() -> aioredis.Redis:
    """Lazy-init shared Redis connection (reused across all calls in this worker)."""
    global _redis
    if _redis is None:
        settings = _get_settings()
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


class ConnectionManager:
    """
    Manages active WebSocket connections for the current worker process.
    Publishes to Redis so other workers can forward events to their connections.
    """

    def __init__(self) -> None:
        # user_id (str) → list of active websockets on THIS worker
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        uid = str(user_id)
        if uid not in self._connections:
            self._connections[uid] = []
        self._connections[uid].append(websocket)
        # Mark presence after the connection is registered so a racing
        # is_online() check never sees "online but no connection".
        from app.services.presence import mark_online
        await mark_online(user_id)

    async def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        """Remove a WebSocket connection. Marks offline if it was the last one."""
        uid = str(user_id)
        if uid in self._connections:
            self._connections[uid] = [ws for ws in self._connections[uid] if ws != websocket]
            if not self._connections[uid]:
                del self._connections[uid]
        from app.services.presence import mark_offline
        await mark_offline(user_id)

    def is_online(self, user_id: uuid.UUID) -> bool:
        """Check if a user has any active connections on this worker."""
        return str(user_id) in self._connections

    async def _deliver_local(self, user_id: str, data: dict) -> None:
        """Deliver data to all local connections for user_id (this worker only)."""
        if user_id not in self._connections:
            return
        dead: list[WebSocket] = []
        for ws in list(self._connections[user_id]):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[user_id] = [w for w in self._connections[user_id] if w != ws]
        if not self._connections.get(user_id):
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: uuid.UUID, data: dict) -> None:
        """
        Send a message to a user.
        Delivers directly to local connections, and publishes to Redis so other
        workers with the user's connection also receive it.
        """
        uid = str(user_id)
        # (a) Deliver to this worker's connections immediately
        await self._deliver_local(uid, data)
        # (b) Publish to Redis for other workers.
        # Wrap with worker ID so our own subscriber skips it — we already
        # delivered locally above and don't want to send twice.
        try:
            r = await _get_redis()
            envelope = json.dumps({"_w": _WORKER_ID, "d": data})
            await r.publish(f"{_WS_CHANNEL_PREFIX}{uid}", envelope)
        except Exception as e:
            logger.warning("Redis publish error for user %s: %s", uid, e)

    async def start_redis_subscriber(self) -> None:
        """
        Long-running coroutine: subscribes to all kaasb:ws:* channels via Redis
        psubscribe and forwards events to local connections.
        Should be started once per worker in the app lifespan.
        """
        while True:
            try:
                r = await _get_redis()
                pubsub = r.pubsub()
                await pubsub.psubscribe(f"{_WS_CHANNEL_PREFIX}*")
                logger.info("Redis WS subscriber started (pattern: %s*)", _WS_CHANNEL_PREFIX)

                async for raw in pubsub.listen():
                    if raw["type"] != "pmessage":
                        continue
                    channel: str = raw["channel"]
                    uid = channel.removeprefix(_WS_CHANNEL_PREFIX)
                    try:
                        outer: dict[str, Any] = json.loads(raw["data"])
                    except (json.JSONDecodeError, TypeError):
                        continue
                    # Skip messages published by THIS worker — it already
                    # delivered them locally in send_to_user._deliver_local.
                    if outer.get("_w") == _WORKER_ID:
                        continue
                    # Extract actual payload (support both enveloped and legacy).
                    payload: dict[str, Any] = outer.get("d", outer)
                    # Only deliver to connections on THIS worker
                    if uid in self._connections:
                        await self._deliver_local(uid, payload)

            except asyncio.CancelledError:
                logger.info("Redis WS subscriber cancelled")
                return
            except Exception as e:
                logger.warning("Redis WS subscriber error, reconnecting in 2s: %s", e)
                await asyncio.sleep(2)


# Singleton — one per worker process
manager = ConnectionManager()


# =========================================================================
# WS Ticket Store (Redis-backed, so any worker can redeem)
# =========================================================================

async def create_ws_ticket(user_id: uuid.UUID) -> str:
    """
    Create a 60-second single-use WebSocket auth ticket stored in Redis.
    Any worker can redeem it (solves httpOnly cookie + multi-worker problem).
    """
    ticket = secrets.token_urlsafe(32)
    key = f"{_TICKET_PREFIX}{ticket}"
    try:
        r = await _get_redis()
        await r.set(key, str(user_id), ex=_TICKET_TTL_SECONDS)
    except Exception as e:
        logger.error("Failed to store WS ticket in Redis: %s", e)
        # Fall back to in-memory for dev environments without Redis
        _ws_tickets_fallback[ticket] = (user_id, datetime.now(UTC) + timedelta(seconds=_TICKET_TTL_SECONDS))
    return ticket


async def redeem_ws_ticket(ticket: str) -> uuid.UUID | None:
    """
    Consume a ticket (single-use) and return the associated user_id.
    Returns None if the ticket is unknown or expired.
    """
    key = f"{_TICKET_PREFIX}{ticket}"
    try:
        r = await _get_redis()
        # GETDEL is atomic: get + delete in one round-trip (Redis 6.2+)
        user_id_str: str | None = await r.getdel(key)
        if user_id_str:
            return uuid.UUID(user_id_str)
    except Exception as e:
        logger.warning("Redis ticket redeem error, trying fallback: %s", e)
        # Fall through to in-memory fallback

    # In-memory fallback (single-worker / dev)
    entry = _ws_tickets_fallback.pop(ticket, None)
    if entry:
        user_id, expires_at = entry
        if datetime.now(UTC) <= expires_at:
            return user_id
    return None


# In-memory fallback for dev environments without Redis
_ws_tickets_fallback: dict[str, tuple[uuid.UUID, datetime]] = {}
