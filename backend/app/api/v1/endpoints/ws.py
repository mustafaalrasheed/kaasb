"""
Kaasb Platform - WebSocket Endpoint
GET /api/v1/ws?ticket=<ws_ticket>  - Real-time notifications and message delivery

Auth flow:
  1. Call POST /api/v1/auth/ws-ticket (cookie auth) → receive 60s single-use ticket
  2. Open WebSocket: ws://host/api/v1/ws?ticket=<ticket>
  3. Server redeems ticket, establishes persistent connection

Events pushed by the server (JSON):
  {"type": "message",        "data": {conversation_id, id, content, sender_id, sender_role,
                                       is_system, attachments, created_at}}
  {"type": "messages_read",  "data": {conversation_id, reader_id, message_ids, read_at}}
  {"type": "typing",         "data": {conversation_id, user_id}}
  {"type": "notification",   "data": {id, title, message, type, link_type, link_id, created_at}}
  {"type": "ping"}

Events accepted from the client:
  {"type": "pong"}                                 — heartbeat reply
  {"type": "typing", "conversation_id": "<uuid>"}  — signal user is typing

Typing events are ephemeral (never persisted) and are rate-limited to at most
one relay per conversation per second, per connection.
"""

import logging
import time
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import async_session
from app.models.message import Conversation
from app.services.websocket_manager import manager, redeem_ws_ticket

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

# Minimum seconds between relayed typing events per conversation per WS.
# Clients are expected to heartbeat typing every ~3s, so 1s gives slack
# without letting a misbehaving client fan out dozens/sec.
_TYPING_MIN_INTERVAL_SECONDS = 1.0


async def _resolve_other_participant(
    user_id: uuid.UUID, conversation_id: uuid.UUID,
) -> uuid.UUID | None:
    """
    Return the OTHER participant's UUID if ``user_id`` is a participant,
    else None. Runs one cheap query; result is cached per connection.
    """
    async with async_session() as db:
        result = await db.execute(
            select(
                Conversation.participant_one_id,
                Conversation.participant_two_id,
            ).where(Conversation.id == conversation_id)
        )
        row = result.first()
        if not row:
            return None
        p1, p2 = row.participant_one_id, row.participant_two_id
        if user_id == p1:
            return p2
        if user_id == p2:
            return p1
        return None


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

    # Per-connection caches:
    #   other_participant[conv_id] = the other user's UUID (populated on first
    #     typing event for that conversation, then reused).
    #   last_typing_emit[conv_id] = monotonic timestamp of last relayed typing
    #     event, used to rate-limit downstream broadcasts.
    other_participant: dict[uuid.UUID, uuid.UUID] = {}
    last_typing_emit: dict[uuid.UUID, float] = {}

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "pong":
                continue  # Heartbeat acknowledged

            if msg_type == "typing":
                raw_conv = data.get("conversation_id")
                if not raw_conv:
                    continue
                try:
                    conv_id = uuid.UUID(raw_conv)
                except (ValueError, TypeError):
                    continue

                # Rate-limit per conversation
                now = time.monotonic()
                last = last_typing_emit.get(conv_id, 0.0)
                if now - last < _TYPING_MIN_INTERVAL_SECONDS:
                    continue

                # Resolve + cache the other participant (validates membership)
                other_id = other_participant.get(conv_id)
                if other_id is None:
                    other_id = await _resolve_other_participant(user_id, conv_id)
                    if other_id is None:
                        continue  # Not a participant, silently drop
                    other_participant[conv_id] = other_id

                last_typing_emit[conv_id] = now
                await manager.send_to_user(other_id, {
                    "type": "typing",
                    "data": {
                        "conversation_id": str(conv_id),
                        "user_id": str(user_id),
                    },
                })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error for user %s: %s", user_id, exc)
    finally:
        await manager.disconnect(user_id, websocket)
        logger.info("WebSocket disconnected: user_id=%s", user_id)
