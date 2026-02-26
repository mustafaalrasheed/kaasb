"""
Kaasb Platform - WebSocket Connection Manager
Manages active WebSocket connections for real-time messaging.
In production, this would use Redis pub/sub for multi-worker support.
"""

import uuid
import json
from typing import Optional
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
