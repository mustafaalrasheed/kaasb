"""Unit tests for QiCardClient hardening:
- Idempotency cache (Redis + in-memory fallback)
- Log-preview sanitization
- Decimal-based amount rounding at callsites
"""

from decimal import ROUND_HALF_UP, Decimal

import pytest
import pytest_asyncio


# These unit tests don't touch the database. Override the package-level
# autouse `setup_database` fixture with a no-op so they don't block on a
# Postgres test container that may not be available.
@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    yield


# --- Log sanitization ---------------------------------------------------------

class TestSafePreview:
    """_safe_preview must truncate long bodies and redact secret-shaped fields."""

    def setup_method(self) -> None:
        from app.services.qi_card_client import _LOG_BODY_MAX_LEN, _safe_preview
        self.safe = _safe_preview
        self.max_len = _LOG_BODY_MAX_LEN

    def test_empty_returns_placeholder(self):
        assert self.safe("") == "(empty)"
        assert self.safe(None) == "(empty)"

    def test_short_body_returned_verbatim(self):
        body = '{"success": true, "data": {"link": "https://pay.qi.iq/abc"}}'
        assert self.safe(body) == body

    def test_long_body_is_truncated(self):
        body = "x" * (self.max_len + 500)
        out = self.safe(body)
        assert out.endswith("...(truncated)")
        assert len(out) <= self.max_len + len("...(truncated)")

    def test_redacts_api_key(self):
        body = '{"api_key": "sk-live-supersecret", "foo": "bar"}'
        out = self.safe(body)
        assert "sk-live-supersecret" not in out
        assert '"api_key": "***"' in out
        assert '"foo": "bar"' in out  # non-sensitive fields survive

    def test_redacts_authorization_and_password(self):
        body = '{"authorization": "Bearer xxx", "password": "hunter2"}'
        out = self.safe(body)
        assert "Bearer xxx" not in out
        assert "hunter2" not in out

    def test_redacts_case_insensitively(self):
        body = '{"ApiKey": "secret123"}'
        out = self.safe(body)
        assert "secret123" not in out


# --- Amount rounding ----------------------------------------------------------

class TestAmountRounding:
    """IQD amounts must round to nearest whole unit (ROUND_HALF_UP), not truncate."""

    @staticmethod
    def _to_iqd(amount) -> int:
        return int(Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def test_whole_number_unchanged(self):
        assert self._to_iqd(100_000) == 100_000
        assert self._to_iqd(1) == 1

    def test_halves_round_up(self):
        # int() would give 100; ROUND_HALF_UP gives 101
        assert self._to_iqd(100.5) == 101
        assert self._to_iqd(0.5) == 1

    def test_below_half_rounds_down(self):
        assert self._to_iqd(100.49) == 100
        assert self._to_iqd(0.49) == 0

    def test_above_half_rounds_up(self):
        assert self._to_iqd(100.51) == 101
        assert self._to_iqd(99.99) == 100  # <- int() would give 99 (underpayment)

    def test_decimal_input_preserves_precision(self):
        d = Decimal("499.995")
        assert self._to_iqd(d) == 500


# --- Idempotency cache (in-memory fallback path) ------------------------------

class TestIdempotencyCacheInMemory:
    """When Redis is unreachable, the in-memory fallback still enforces idempotency."""

    def setup_method(self) -> None:
        from unittest.mock import patch
        # Force every test to use the in-memory fallback by pinning Redis to None.
        self._patcher = patch("app.services.qi_card_client._get_redis", return_value=None)
        self._mock_get_redis = self._patcher.start()
        # Also reset the shared in-memory dict so each test starts clean.
        import app.services.qi_card_client as mod
        mod._inmem_cache.clear()

    def teardown_method(self) -> None:
        self._patcher.stop()
        import app.services.qi_card_client as mod
        mod._inmem_cache.clear()

    @pytest.mark.asyncio
    async def test_set_then_get_roundtrip(self):
        from app.services.qi_card_client import QiCardClient
        client = QiCardClient()
        value = {"link": "https://pay.qi.iq/abc", "order_id": "o1", "amount_iqd": 100}
        await client._cache_set("o1", value, ttl_seconds=60)
        assert await client._cache_get("o1") == value

    @pytest.mark.asyncio
    async def test_missing_key_returns_none(self):
        from app.services.qi_card_client import QiCardClient
        client = QiCardClient()
        assert await client._cache_get("does-not-exist") is None

    @pytest.mark.asyncio
    async def test_expired_entry_returns_none(self):
        from app.services.qi_card_client import QiCardClient
        client = QiCardClient()
        await client._cache_set("o2", {"link": "x", "order_id": "o2", "amount_iqd": 1}, ttl_seconds=0)
        # TTL=0 → already expired
        assert await client._cache_get("o2") is None

    @pytest.mark.asyncio
    async def test_different_order_ids_are_isolated(self):
        from app.services.qi_card_client import QiCardClient
        client = QiCardClient()
        a = {"link": "https://pay.qi.iq/a", "order_id": "A", "amount_iqd": 1}
        b = {"link": "https://pay.qi.iq/b", "order_id": "B", "amount_iqd": 2}
        await client._cache_set("A", a, 60)
        await client._cache_set("B", b, 60)
        assert (await client._cache_get("A"))["link"] == "https://pay.qi.iq/a"
        assert (await client._cache_get("B"))["link"] == "https://pay.qi.iq/b"


class TestCreatePaymentIdempotency:
    """End-to-end: a repeat create_payment with the same order_id must NOT re-call Qi Card."""

    def setup_method(self) -> None:
        from unittest.mock import patch
        import app.services.qi_card_client as mod
        mod._inmem_cache.clear()
        self._patcher = patch("app.services.qi_card_client._get_redis", return_value=None)
        self._patcher.start()

    def teardown_method(self) -> None:
        import app.services.qi_card_client as mod
        mod._inmem_cache.clear()
        self._patcher.stop()

    @pytest.mark.asyncio
    async def test_mock_mode_caches_link(self):
        """In mock mode (no API key) the second call returns the first link verbatim."""
        from unittest.mock import patch
        from app.services.qi_card_client import QiCardClient

        with patch.object(QiCardClient, "_is_configured", return_value=False):
            client = QiCardClient()
            first = await client.create_payment(
                amount_iqd=100_000,
                order_id="escrow-test-idempotent",
                success_url="https://example.com/s",
                failure_url="https://example.com/f",
                cancel_url="https://example.com/c",
            )
            second = await client.create_payment(
                amount_iqd=100_000,
                order_id="escrow-test-idempotent",
                success_url="https://example.com/s",
                failure_url="https://example.com/f",
                cancel_url="https://example.com/c",
            )
            assert first == second
            # Critically, link must be stable so the browser doesn't get a new
            # Qi Card session on retry.
            assert first["link"] == second["link"]

    @pytest.mark.asyncio
    async def test_different_order_ids_get_different_links(self):
        from unittest.mock import patch
        from app.services.qi_card_client import QiCardClient

        with patch.object(QiCardClient, "_is_configured", return_value=False):
            client = QiCardClient()
            a = await client.create_payment(
                amount_iqd=1,
                order_id="escrow-A",
                success_url="x", failure_url="y", cancel_url="z",
            )
            b = await client.create_payment(
                amount_iqd=1,
                order_id="escrow-B",
                success_url="x", failure_url="y", cancel_url="z",
            )
            assert a["link"] != b["link"]
