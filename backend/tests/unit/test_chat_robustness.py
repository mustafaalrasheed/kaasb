"""Unit tests for PR-C3 chat robustness.

Source-level checks that catch regressions cheaply; full WS integration
tests are out of scope here (they'd need a real uvicorn + event loop).

- Server-side ping heartbeat scheduled on WS connect
- Typing cache entries carry a TTL (no more stale-forever membership)
- Attachment upload endpoint exists and wires through save_chat_attachment
- save_chat_attachment enforces MIME whitelist + path traversal + magic bytes
"""

import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    yield


BACKEND = pathlib.Path(__file__).resolve().parents[2] / "app"


class TestWsPingHeartbeat:
    """ws.py schedules a _ping_loop background task on connect and cancels
    it on disconnect."""

    def test_source_schedules_and_cancels_ping_task(self):
        src = (BACKEND / "api" / "v1" / "endpoints" / "ws.py").read_text()
        # The ping loop function and its scheduling must both exist, and the
        # finally block must cancel the task when the connection drops.
        assert "_ping_loop" in src
        assert "asyncio.create_task(_ping_loop())" in src
        assert "ping_task.cancel()" in src

    def test_source_has_ping_interval_constant(self):
        src = (BACKEND / "api" / "v1" / "endpoints" / "ws.py").read_text()
        # Interval is defined at module scope so tests + ops can reason about
        # it. Value should sit under the typical 60s idle-timeout window.
        assert "_PING_INTERVAL_SECONDS" in src

    def test_source_sends_ping_json_type(self):
        src = (BACKEND / "api" / "v1" / "endpoints" / "ws.py").read_text()
        # The payload must carry the "ping" type so the client's pong
        # handler matches.
        assert '"type": "ping"' in src


class TestTypingCacheTTL:
    """The other_participant cache is now a (id, cached_at) tuple and the
    typing handler checks the age against _TYPING_CACHE_TTL_SECONDS."""

    def test_source_uses_ttl_constant(self):
        src = (BACKEND / "api" / "v1" / "endpoints" / "ws.py").read_text()
        assert "_TYPING_CACHE_TTL_SECONDS" in src

    def test_source_stores_cached_at(self):
        src = (BACKEND / "api" / "v1" / "endpoints" / "ws.py").read_text()
        # The dict value shape must include a timestamp so expiry works.
        assert "tuple[uuid.UUID, float]" in src
        # Expiry check is against the monotonic `now` captured for the
        # rate-limit path.
        assert "now - cached_at" in src


class TestAttachmentUpload:
    """POST /messages/attachments exists, calls save_chat_attachment, and
    is authenticated."""

    def test_endpoint_declared(self):
        src = (BACKEND / "api" / "v1" / "endpoints" / "messages.py").read_text()
        assert '"/attachments"' in src
        # The function must take an authenticated current_user so anonymous
        # uploads can't plant garbage in the attachments directory.
        assert "current_user: User = Depends(get_current_user)" in src
        assert "save_chat_attachment" in src

    def test_endpoint_returns_attachment_shape(self):
        """The handler must return whatever save_chat_attachment returns;
        the downstream consumer is MessageCreate.attachments which expects
        the {url, filename, mime_type, size_bytes} contract enforced by
        MessageAttachment. If the handler accidentally wraps the dict or
        adds keys, validation on send_message would reject it silently."""
        src = (BACKEND / "api" / "v1" / "endpoints" / "messages.py").read_text()
        # Simple substring check — the handler must return the service call
        # directly rather than wrapping it in another dict/shape.
        assert "return await save_chat_attachment(" in src


class TestSaveChatAttachment:
    """utils/files.py save_chat_attachment enforces the documented rules."""

    @pytest.mark.asyncio
    async def test_rejects_disallowed_mime(self):
        from fastapi import HTTPException
        from app.utils.files import save_chat_attachment

        file = MagicMock()
        file.filename = "evil.exe"
        file.content_type = "application/x-msdownload"
        # read() would never be called because content_type rejects first —
        # set a side effect that would fail the test if reached.
        file.read = AsyncMock(side_effect=AssertionError("must not read body"))

        with pytest.raises(HTTPException) as exc:
            await save_chat_attachment(file, user_id="u1")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_path_traversal_filename(self):
        from fastapi import HTTPException
        from app.utils.files import save_chat_attachment

        file = MagicMock()
        file.filename = "../../etc/passwd"
        file.content_type = "application/pdf"
        file.read = AsyncMock(side_effect=AssertionError("must not read body"))

        with pytest.raises(HTTPException) as exc:
            await save_chat_attachment(file, user_id="u1")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_image_with_wrong_magic_bytes_rejected(self):
        from fastapi import HTTPException
        from app.utils.files import save_chat_attachment

        # Claims PNG but sends PDF magic bytes — must be rejected.
        file = MagicMock()
        file.filename = "fake.png"
        file.content_type = "image/png"
        chunks = [b"%PDF-1.4\n...fake..."]

        async def _read(n: int):
            return chunks.pop(0) if chunks else b""
        file.read = _read

        with pytest.raises(HTTPException) as exc:
            await save_chat_attachment(file, user_id="u1")
        assert exc.value.status_code == 400
        assert "does not match" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_size_over_limit_rejected(self):
        from fastapi import HTTPException
        from app.core.config import get_settings
        from app.utils.files import save_chat_attachment

        limit = get_settings().MAX_UPLOAD_SIZE_MB * 1024 * 1024
        # Stream one chunk that already exceeds the limit.
        big = [b"x" * (limit + 64 * 1024)]

        async def _read(n: int):
            return big.pop(0) if big else b""

        file = MagicMock()
        file.filename = "big.pdf"
        file.content_type = "application/pdf"
        file.read = _read

        with pytest.raises(HTTPException) as exc:
            await save_chat_attachment(file, user_id="u1")
        assert exc.value.status_code == 400
        assert "too large" in exc.value.detail.lower()


class TestFrontendSeenIdDedup:
    """Source-level guard that the frontend WS hook tracks a seen-message-ID
    Set and short-circuits duplicate deliveries."""

    def test_hook_defines_seen_ids_ref(self):
        hook_src = (
            pathlib.Path(__file__).resolve().parents[3]
            / "frontend" / "src" / "lib" / "use-websocket.ts"
        ).read_text()
        assert "seenMessageIdsRef" in hook_src
        assert "_SEEN_ID_CAP" in hook_src
        # The dedup branch must fire on the "message" event, not on
        # "notification" (which has its own idempotency via notification_id
        # semantics in NotificationService).
        assert 'parsed.type === "message"' in hook_src
        assert "seenMessageIdsRef.current.has(" in hook_src
