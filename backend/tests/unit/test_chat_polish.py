"""Unit tests for PR-C4 chat polish: per-type masking copy, Redis subscriber
exponential backoff, frontend reconnect timer cleanup."""

import pathlib

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    yield


BACKEND = pathlib.Path(__file__).resolve().parents[2] / "app"
FRONTEND = pathlib.Path(__file__).resolve().parents[3] / "frontend" / "src"


class TestMaskingUXPerType:
    """mask_content swaps a per-type placeholder so the sender knows what
    tripped the filter, not just a generic 'contact info removed'."""

    def test_email_has_dedicated_placeholder(self):
        from app.services.message_filter_service import mask_content

        out = mask_content("ping me at alice@example.com please")
        assert "email removed" in out
        # The generic fallback wording must NOT appear — that was the
        # pre-PR-C4 copy. Keep it out so we don't regress the UX hint.
        assert "contact info removed" not in out

    def test_phone_has_dedicated_placeholder(self):
        from app.services.message_filter_service import mask_content

        out = mask_content("call me on 07812345678")
        assert "phone removed" in out

    def test_url_has_dedicated_placeholder(self):
        from app.services.message_filter_service import mask_content

        out = mask_content("check https://fakekaasb.com/offer")
        assert "external link removed" in out

    def test_app_has_dedicated_placeholder(self):
        from app.services.message_filter_service import mask_content

        out = mask_content("find me on whatsapp")
        assert "external app removed" in out

    def test_kaasb_url_not_masked(self):
        """Allow-listed URLs still pass through untouched after the copy
        change — regression guard on _is_allowed_url."""
        from app.services.message_filter_service import mask_content

        out = mask_content("here: https://kaasb.com/jobs/42")
        assert "https://kaasb.com/jobs/42" in out
        assert "link removed" not in out


class TestRedisSubscriberExponentialBackoff:
    def test_source_uses_exponential_backoff(self):
        src = (BACKEND / "services" / "websocket_manager.py").read_text()
        # The flat 2s sleep is gone. The retry path must compute a delay
        # that grows with the attempt counter and resets on success.
        assert "min(2 ** attempt, 30)" in src
        assert "attempt = 0" in src
        # The old flat sleep comment shouldn't survive.
        assert "reconnecting in 2s" not in src


class TestFrontendReconnectTimerLeak:
    def test_schedule_reconnect_short_circuits_on_unmount(self):
        src = (FRONTEND / "lib" / "use-websocket.ts").read_text()
        # scheduleReconnect must now guard on mountedRef before scheduling
        # AND clear its own ref inside the setTimeout callback so the
        # cleanup effect sees a null and skips a stale clearTimeout.
        # Simpler regression guard: the function body references mountedRef.
        func_start = src.find("function scheduleReconnect()")
        func_end = src.find("\n  }", func_start)
        assert func_start != -1 and func_end != -1
        body = src[func_start:func_end]
        assert "mountedRef.current" in body
        # The timer id is cleared inside the setTimeout callback so
        # cleanup doesn't need to touch it after firing.
        assert "reconnectTimer.current = null" in body


class TestNormalizationFromC1StillWorks:
    """Regression guard — the C1 normalization path must keep working after
    the C4 masking copy update."""

    def test_zero_width_still_stripped(self):
        from app.services.message_filter_service import detect_violations
        from app.models.violation_log import ViolationType

        # Same ZWSP evasion as C1's test — re-run here to make sure the
        # copy change didn't accidentally break NFKC pre-processing.
        found = detect_violations("use what​sapp to talk")
        assert any(v[0] == ViolationType.EXTERNAL_APP for v in found)
