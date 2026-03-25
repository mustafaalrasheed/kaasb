"""Unit tests for input sanitization utilities."""

from app.utils.sanitize import sanitize_text, sanitize_username, sanitize_email, sanitize_url, escape_like


class TestSanitizeText:
    def test_strips_script_tags(self):
        assert "<script>" not in sanitize_text("<script>alert('xss')</script>Hello")

    def test_preserves_normal_text(self):
        assert sanitize_text("Hello World") == "Hello World"

    def test_enforces_max_length(self):
        long_text = "A" * 500
        result = sanitize_text(long_text, max_length=100)
        assert len(result) <= 100

    def test_strips_html_tags(self):
        result = sanitize_text("<b>bold</b> <i>italic</i>")
        assert "<b>" not in result
        assert "<i>" not in result


class TestSanitizeUsername:
    def test_allows_valid_username(self):
        assert sanitize_username("john_doe-123") == "john_doe-123"

    def test_strips_invalid_chars(self):
        result = sanitize_username("john@doe!#$")
        assert "@" not in result
        assert "!" not in result


class TestSanitizeEmail:
    def test_lowercases_email(self):
        assert sanitize_email("User@Example.COM") == "user@example.com"

    def test_strips_whitespace(self):
        assert sanitize_email("  user@test.com  ") == "user@test.com"


class TestSanitizeUrl:
    def test_allows_https(self):
        assert sanitize_url("https://example.com") == "https://example.com"

    def test_blocks_javascript_uri(self):
        result = sanitize_url("javascript:alert(1)")
        assert result == ""


class TestEscapeLike:
    def test_escapes_percent(self):
        assert "%" not in escape_like("50%")

    def test_escapes_underscore(self):
        assert escape_like("hello_world") == r"hello\_world"

    def test_normal_text_unchanged(self):
        assert escape_like("hello") == "hello"
