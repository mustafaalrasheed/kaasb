"""Unit tests for payment security: HMAC signing, OTP randomness, sanitization."""

import hashlib
import hmac
import secrets

import pytest


class TestPaymentHMACSigning:
    """HMAC signature must protect success URLs from forgery."""

    def _sign(self, order_id: str, secret_key: str = "test-secret-key") -> str:
        return hmac.new(secret_key.encode(), order_id.encode(), hashlib.sha256).hexdigest()

    def _verify(self, order_id: str, sig: str, secret_key: str = "test-secret-key") -> bool:
        if not sig:
            return False
        expected = self._sign(order_id, secret_key)
        return hmac.compare_digest(expected, sig)

    def test_valid_signature_accepted(self):
        order_id = "gig-order-12345678-1234-1234-1234-123456789abc"
        sig = self._sign(order_id)
        assert self._verify(order_id, sig) is True

    def test_wrong_order_id_rejected(self):
        sig = self._sign("gig-order-legitimate")
        assert self._verify("gig-order-attacker", sig) is False

    def test_empty_signature_rejected(self):
        assert self._verify("gig-order-abc", "") is False

    def test_tampered_signature_rejected(self):
        sig = self._sign("gig-order-abc")
        tampered = sig[:-4] + "0000"
        assert self._verify("gig-order-abc", tampered) is False

    def test_different_secret_rejected(self):
        sig = self._sign("gig-order-abc", "attacker-secret")
        assert self._verify("gig-order-abc", sig, "real-secret") is False

    def test_signature_is_constant_length(self):
        sig1 = self._sign("short")
        sig2 = self._sign("a" * 500)
        # SHA-256 hexdigest is always 64 chars regardless of input length
        assert len(sig1) == 64
        assert len(sig2) == 64

    def test_escrow_and_gig_order_ids_produce_different_sigs(self):
        uuid_part = "12345678-1234-1234-1234-123456789abc"
        assert self._sign(f"escrow-{uuid_part}") != self._sign(f"gig-order-{uuid_part}")


class TestOTPSecurity:
    """OTP generation must be cryptographically secure and in range."""

    def test_otp_in_valid_range(self):
        for _ in range(1000):
            otp = secrets.randbelow(900000) + 100000
            assert 100000 <= otp <= 999999

    def test_otp_is_6_digits(self):
        for _ in range(1000):
            otp = str(secrets.randbelow(900000) + 100000)
            assert len(otp) == 6

    def test_otp_not_all_same(self):
        """Very basic bias check: generate 100 OTPs, expect some variation."""
        otps = {secrets.randbelow(900000) + 100000 for _ in range(100)}
        assert len(otps) > 50, "Too many collisions — check randomness source"

    def test_random_module_not_used(self):
        """Ensure the auth_service module no longer imports the 'random' stdlib module."""
        import importlib
        import sys

        # Remove cached module to get fresh import
        mod_name = "app.services.auth_service"
        if mod_name in sys.modules:
            del sys.modules[mod_name]

        import ast
        import pathlib

        src = pathlib.Path("app/services/auth_service.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "random", (
                        "auth_service.py still imports 'random' — use 'secrets' instead"
                    )
            elif isinstance(node, ast.ImportFrom):
                assert node.module != "random", (
                    "auth_service.py still imports from 'random' — use 'secrets' instead"
                )


class TestSanitizeText:
    """sanitize_text must strip dangerous content but not html.escape plain text."""

    def setup_method(self):
        from app.utils.sanitize import sanitize_text
        self.sanitize = sanitize_text

    def test_strips_script_tag(self):
        result = self.sanitize("<script>alert(1)</script>")
        assert "<script>" not in result
        assert "alert" in result or result == ""

    def test_strips_html_tags(self):
        result = self.sanitize("<b>bold</b>")
        assert "<b>" not in result

    def test_does_not_escape_ampersand(self):
        """Ahmed & Ali must NOT be stored as Ahmed &amp; Ali in a JSON API."""
        result = self.sanitize("Ahmed & Ali")
        assert result == "Ahmed & Ali", f"Expected 'Ahmed & Ali', got '{result}'"

    def test_does_not_escape_quotes(self):
        result = self.sanitize("it's a \"test\"")
        assert "&quot;" not in result
        assert "&#x27;" not in result

    def test_plain_text_passes_through(self):
        result = self.sanitize("Hello World")
        assert result == "Hello World"

    def test_null_bytes_stripped(self):
        result = self.sanitize("hello\x00world")
        assert "\x00" not in result

    def test_removes_event_handlers(self):
        result = self.sanitize("click me onclick=alert(1)")
        assert "onclick=" not in (result or "")

    def test_removes_javascript_uri(self):
        result = self.sanitize("javascript:alert(1)")
        assert "javascript:" not in (result or "")

    def test_max_length_enforced(self):
        result = self.sanitize("a" * 20000, max_length=100)
        assert len(result) <= 100


class TestPaymentServiceSignature:
    """Test PaymentService._sign_order_id and _verify_order_sig methods."""

    def setup_method(self):
        # Patch settings before importing PaymentService
        from unittest.mock import MagicMock, patch
        self.settings_patcher = patch("app.services.payment_service.settings")
        self.mock_settings = self.settings_patcher.start()
        self.mock_settings.SECRET_KEY = "test-secret"
        self.mock_settings.PLATFORM_FEE_PERCENT = 10.0
        self.mock_settings.QI_CARD_CURRENCY = "IQD"
        self.mock_settings.QI_CARD_SANDBOX = True
        self.mock_settings.DOMAIN = "localhost"

    def teardown_method(self):
        self.settings_patcher.stop()

    def test_sign_and_verify_roundtrip(self):
        from unittest.mock import MagicMock
        from app.services.payment_service import PaymentService

        svc = PaymentService.__new__(PaymentService)
        order_id = "escrow-abc123"
        sig = svc._sign_order_id(order_id)
        assert svc._verify_order_sig(order_id, sig) is True

    def test_empty_sig_rejected(self):
        from app.services.payment_service import PaymentService

        svc = PaymentService.__new__(PaymentService)
        assert svc._verify_order_sig("escrow-abc", "") is False

    def test_wrong_order_id_rejected(self):
        from app.services.payment_service import PaymentService

        svc = PaymentService.__new__(PaymentService)
        sig = svc._sign_order_id("escrow-real")
        assert svc._verify_order_sig("escrow-fake", sig) is False
