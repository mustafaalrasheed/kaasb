"""
Kaasb Platform - WebSocket Endpoint
GET /api/v1/ws?token=<jwt>  - Real-time notifications and message delivery

Per-worker in-memory state: messages only reach clients connected to the same
Gunicorn worker. Redis pub/sub upgrade is tracked in CLAUDE.md known limitations.
"""

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.database import async_session as async_session_factory
from app.services.auth_service import AuthService
from app.services.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    Establish a WebSocket connection for real-time events.

    Connect with:  wss://kaasb.com/api/v1/ws?token=<access_token>

    Events pushed by the server (JSON):
      {"type": "notification", "data": {...}}
      {"type": "message",      "data": {...}}
      {"type": "ping"}

    Client should respond to {"type": "ping"} with {"type": "pong"}.
    The connection is closed by the server on token expiry or account deactivation.
    """
    # Authenticate before accepting the connection
    async with async_session_factory() as db:
        auth_service = AuthService(db)
        try:
            user = await auth_service.get_current_user(token)
        except Exception:
            await websocket.close(code=4001)
            return

    user_id = user.id

    await manager.connect(user_id, websocket)
    logger.info("WebSocket connected: user_id=%s", user_id)

    try:
        while True:
            # Keep connection alive; react to client messages (e.g. pong)
            data = await websocket.receive_json()
            if data.get("type") == "pong":
                pass  # heartbeat acknowledged
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error for user %s: %s", user_id, exc)
    finally:
        manager.disconnect(user_id, websocket)
        logger.info("WebSocket disconnected: user_id=%s", user_id)
