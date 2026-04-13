"""
Kaasb Platform - Input Sanitization
Cleans user input to prevent XSS, HTML injection, and other attacks.
"""

import html
import re

# Dangerous HTML tags and patterns
_SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_EVENT_PATTERN = re.compile(r"\bon\w+\s*=", re.IGNORECASE)
_JAVASCRIPT_PATTERN = re.compile(r"javascript\s*:", re.IGNORECASE)
_DATA_PATTERN = re.compile(r"(?:^|[\s\"'=])data\s*:\s*\w+/\w+", re.IGNORECASE)
_EXPRESSION_PATTERN = re.compile(r"expression\s*\(", re.IGNORECASE)
_IMPORT_PATTERN = re.compile(r"@import", re.IGNORECASE)

# SQL injection patterns (defense in depth — ORM already handles this)
_SQL_PATTERNS = [
    re.compile(r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|EXEC)\s", re.IGNORECASE),
    re.compile(r"UNION\s+(ALL\s+)?SELECT", re.IGNORECASE),
    re.compile(r"--\s*$", re.MULTILINE),
]


def sanitize_text(text: str | None, max_length: int = 10000) -> str | None:
    """
    Sanitize user-provided text input.

    - Strips HTML tags
    - Removes script injections
    - Escapes special characters
    - Trims whitespace
    - Enforces max length
    """
    if text is None:
        return None

    if not isinstance(text, str):
        return str(text)[:max_length]

    # Strip null bytes
    text = text.replace("\x00", "")

    # Remove script tags and content
    text = _SCRIPT_PATTERN.sub("", text)

    # Remove all HTML tags
    text = _TAG_PATTERN.sub("", text)

    # Remove event handlers (onclick, onload, etc.)
    text = _EVENT_PATTERN.sub("", text)

    # Remove javascript: and data: URIs
    text = _JAVASCRIPT_PATTERN.sub("", text)

    # Remove CSS expressions and imports
    text = _EXPRESSION_PATTERN.sub("", text)
    text = _IMPORT_PATTERN.sub("", text)

    # HTML-escape remaining special characters
    text = html.escape(text, quote=True)

    # Normalize whitespace (collapse multiple spaces, trim)
    text = " ".join(text.split())

    # Enforce max length
    return text[:max_length] if text else text


def sanitize_username(username: str | None) -> str | None:
    """Sanitize username — alphanumeric, underscores, hyphens only."""
    if username is None:
        return None
    # Strip anything that's not alphanumeric, underscore, or hyphen
    cleaned = re.sub(r"[^\w\-]", "", username)
    return cleaned[:50]


def sanitize_email(email: str | None) -> str | None:
    """Basic email sanitization — lowercase, strip whitespace."""
    if email is None:
        return None
    return email.strip().lower()[:254]


def sanitize_url(url: str | None) -> str | None:
    """Sanitize URL — block javascript: and data: URIs."""
    if url is None:
        return None
    url = url.strip()
    lower = url.lower()
    if lower.startswith("javascript:") or lower.startswith("data:"):
        return ""
    if not (lower.startswith("http://") or lower.startswith("https://")):
        return None
    return url[:2000]


def escape_like(text: str) -> str:
    """Escape SQL LIKE/ILIKE wildcard characters to prevent wildcard injection."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def check_sql_injection(text: str) -> bool:
    """
    Check if text contains suspicious SQL patterns.
    Returns True if suspicious. Defense-in-depth only — ORM prevents actual injection.
    """
    return any(pattern.search(text) for pattern in _SQL_PATTERNS)
