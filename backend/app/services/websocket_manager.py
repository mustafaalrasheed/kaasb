"""
Kaasb Platform - WebSocket Connection Manager
Manages active WebSocket connections for real-time messaging.
In production, this would use Redis pub/sub for multi-worker support.

WS Ticket flow (solves httpOnly cookie problem):
  1. Frontend calls POST /auth/ws-ticket (authenticated via cookie) → gets 60s ticket
  2. Frontend opens WebSocket with ?ticket=<ticket>
  3. ws.py redeems ticket (single-use) and registers the connection
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self):
        # user_id -> list of active websockets (user may have multiple tabs)
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        uid = str(user_id)
        if uid not in self._connections:
            self._connections[uid] = []
        self._connections[uid].append(websocket)

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket):
        """Remove a WebSocket connection."""
        uid = str(user_id)
        if uid in self._connections:
            self._connections[uid] = [
                ws for ws in self._connections[uid] if ws != websocket
            ]
            if not self._connections[uid]:
                del self._connections[uid]

    def is_online(self, user_id: uuid.UUID) -> bool:
        """Check if a user has any active connections."""
        return str(user_id) in self._connections

    async def send_to_user(self, user_id: uuid.UUID, data: dict):
        """Send a message to all of a user's active connections."""
        uid = str(user_id)
        if uid in self._connections:
            dead = []
            for ws in self._connections[uid]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            # Clean up dead connections
            for ws in dead:
                self._connections[uid] = [
                    w for w in self._connections[uid] if w != ws
                ]
            if not self._connections.get(uid):
                self._connections.pop(uid, None)


# Singleton instance
manager = ConnectionManager()

# === WS Ticket Store (in-memory, per-worker) ===
# ticket_str → (user_id, expires_at)
_ws_tickets: dict[str, tuple[uuid.UUID, datetime]] = {}


def create_ws_ticket(user_id: uuid.UUID) -> str:
    """Create a 60-second single-use WebSocket auth ticket.
    Solves the httpOnly cookie problem: the frontend calls POST /auth/ws-ticket
    (authenticated via cookie) and receives a short-lived opaque token it can
    pass as a WebSocket query parameter.
    """
    # Purge expired tickets to prevent unbounded growth
    now = datetime.now(UTC)
    expired_keys = [k for k, (_, exp) in _ws_tickets.items() if exp < now]
    for k in expired_keys:
        del _ws_tickets[k]

    ticket = secrets.token_urlsafe(32)
    _ws_tickets[ticket] = (user_id, now + timedelta(seconds=60))
    return ticket


def redeem_ws_ticket(ticket: str) -> uuid.UUID | None:
    """Consume a ticket (single-use) and return the associated user_id.
    Returns None if the ticket is unknown or expired.
    """
    entry = _ws_tickets.pop(ticket, None)
    if not entry:
        return None
    user_id, expires_at = entry
    if datetime.now(UTC) > expires_at:
        return None
    return user_id
