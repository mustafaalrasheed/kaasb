"""
Kaasb Platform - WebSocket Endpoint
GET /api/v1/ws?ticket=<ws_ticket>  - Real-time notifications and message delivery

Auth flow:
  1. Call POST /api/v1/auth/ws-ticket (cookie auth) → receive 60s single-use ticket
  2. Open WebSocket: ws://host/api/v1/ws?ticket=<ticket>
  3. Server redeems ticket, establishes persistent connection

Events pushed by the server (JSON):
  {"type": "message",      "data": {conversation_id, id, content, sender_id, created_at}}
  {"type": "notification", "data": {id, title, message, type, link_type, link_id, created_at}}
  {"type": "ping"}

Client must respond to {"type": "ping"} with {"type": "pong"} to keep connection alive.

Per-worker limitation: connections are tracked in-process memory.
Multi-worker real-time requires Redis pub/sub (tracked in known issues).
"""

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import manager, redeem_ws_ticket

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ticket: str = Query(..., description="Short-lived WS auth ticket from POST /auth/ws-ticket"),
):
    """
    Establish a WebSocket connection for real-time events.

    Requires a short-lived ticket obtained from POST /api/v1/auth/ws-ticket.
    Tickets expire after 60 seconds and are single-use.
    """
    # Redeem the ticket — single use, expires in 60s (Redis-backed)
    user_id = await redeem_ws_ticket(ticket)
    if not user_id:
        await websocket.close(code=4001)
        logger.warning("WebSocket rejected: invalid or expired ticket")
        return

    await manager.connect(user_id, websocket)
    logger.info("WebSocket connected: user_id=%s", user_id)

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "pong":
                pass  # Heartbeat acknowledged
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error for user %s: %s", user_id, exc)
    finally:
        manager.disconnect(user_id, websocket)
        logger.info("WebSocket disconnected: user_id=%s", user_id)
