"""
Unit tests for the off-platform-contact filter (F6).

These exercise the pure functions — ``detect_violations``, ``mask_content``,
``_is_allowed_url`` — so no DB / no async fixtures. Regressions in the regex
patterns are what let users smuggle contact info past the filter, so this
file gets updated every time the patterns change.

The ``MessageFilterService.process_message`` integration (escalation ladder,
DB writes, notification fan-out) is covered in integration tests.
"""

from app.models.message import ConversationType
from app.models.violation_log import ViolationType
from app.services.message_filter_service import (
    _is_allowed_url,
    detect_violations,
    mask_content,
)


def _types(violations):
    """Convenience: extract just the ViolationType set from a detect result."""
    return {v[0] for v in violations}


class TestDetectEmail:
    def test_plain_email(self):
        assert ViolationType.EMAIL in _types(detect_violations("reach me at foo@bar.com"))

    def test_obfuscated_with_spaces_around_at(self):
        # The pattern explicitly tolerates whitespace around `@` and `.`.
        assert ViolationType.EMAIL in _types(
            detect_violations("my address is foo @ bar . com")
        )

    def test_no_email_no_violation(self):
        assert detect_violations("hello, how are you?") == []

    def test_mixed_case(self):
        assert ViolationType.EMAIL in _types(detect_violations("Foo.Bar@EXAMPLE.COM"))


class TestDetectPhone:
    def test_iraqi_mobile_07xx(self):
        assert ViolationType.PHONE in _types(detect_violations("call 07701234567"))

    def test_iraqi_mobile_with_country_code(self):
        assert ViolationType.PHONE in _types(detect_violations("+9647701234567"))

    def test_phone_with_dashes(self):
        assert ViolationType.PHONE in _types(detect_violations("0770-123-4567"))

    def test_bare_digits_not_matched(self):
        # Intentional: the bare \d{10,13} catch-all was dropped to stop
        # flagging credit card numbers. Only anchored Iraqi / international
        # formats trigger now.
        assert detect_violations("my number is 1234567890") == []

    def test_international_requires_plus(self):
        # Explicit international pattern requires a leading `+` so that a
        # 13-digit number with no prefix (common CC length) doesn't trip it.
        assert ViolationType.PHONE in _types(detect_violations("+1 555 123 4567"))


class TestDetectUrl:
    def test_http_url(self):
        assert ViolationType.URL in _types(
            detect_violations("see https://evil.com/order")
        )

    def test_www_url(self):
        assert ViolationType.URL in _types(detect_violations("www.example.com/path"))

    def test_bare_domain_with_path(self):
        assert ViolationType.URL in _types(
            detect_violations("check example.com/work")
        )

    def test_kaasb_url_allowed(self):
        # Platform URLs must pass through so we don't block our own links.
        violations = detect_violations("open https://kaasb.com/jobs/123")
        assert ViolationType.URL not in _types(violations)

    def test_skip_urls_flag_bypasses_url_but_not_email(self):
        # ORDER conversations share deliverable links; URLs are allowed but
        # email/phone/external-app patterns are still enforced.
        content = "delivery: https://drive.google.com/xyz, contact foo@bar.com"
        types = _types(detect_violations(content, skip_urls=True))
        assert ViolationType.URL not in types
        assert ViolationType.EMAIL in types


class TestDetectExternalApp:
    def test_whatsapp_en(self):
        assert ViolationType.EXTERNAL_APP in _types(
            detect_violations("let's switch to whatsapp")
        )

    def test_whatsapp_ar(self):
        # Arabic users commonly write واتساب.
        assert ViolationType.EXTERNAL_APP in _types(detect_violations("تواصل واتساب"))

    def test_telegram_en_and_ar(self):
        en = _types(detect_violations("my telegram is @foo"))
        ar = _types(detect_violations("أنا على تلغرام"))
        assert ViolationType.EXTERNAL_APP in en
        assert ViolationType.EXTERNAL_APP in ar

    def test_skype_viber_signal(self):
        for term in ("skype", "viber", "signal"):
            assert ViolationType.EXTERNAL_APP in _types(
                detect_violations(f"reach me via {term}")
            ), term


class TestIsAllowedUrl:
    def test_kaasb_host(self):
        assert _is_allowed_url("https://kaasb.com/jobs")

    def test_kaasb_with_subpath(self):
        assert _is_allowed_url("https://kaasb.com/profile/foo")

    def test_random_host_rejected(self):
        assert not _is_allowed_url("https://malicious.example.com/x")


class TestMaskContent:
    def test_masks_email(self):
        masked = mask_content("reach me at foo@bar.com please")
        assert "foo@bar.com" not in masked
        # Per-type bilingual placeholder — checked via the EN half so the
        # test doesn't fight RTL copy changes on the AR half.
        assert "email removed" in masked

    def test_masks_phone(self):
        masked = mask_content("call 07701234567")
        assert "07701234567" not in masked
        assert "phone removed" in masked

    def test_masks_url_but_preserves_kaasb(self):
        content = "see https://evil.com and https://kaasb.com/jobs"
        masked = mask_content(content)
        assert "evil.com" not in masked
        assert "https://kaasb.com/jobs" in masked

    def test_skip_urls_leaves_urls_intact(self):
        # Mirrors the ORDER-type pass-through in detect_violations.
        content = "delivery link: https://drive.google.com/xyz"
        masked = mask_content(content, skip_urls=True)
        assert "https://drive.google.com/xyz" in masked

    def test_masks_external_app_names(self):
        masked = mask_content("ping me on whatsapp")
        assert "whatsapp" not in masked.lower()


class TestSkipUrlsMirrorsOrderType:
    """
    The MessageFilterService decides to skip URL checks based on
    conversation_type; these tests lock in that contract so callers can
    rely on ``ConversationType.ORDER`` being the one that bypasses URLs.
    """

    def test_order_type_value(self):
        # If this ever changes, callers of the filter break silently.
        assert ConversationType.ORDER.value == "order"

    def test_user_type_value(self):
        assert ConversationType.USER.value == "user"

    def test_support_type_value(self):
        assert ConversationType.SUPPORT.value == "support"
