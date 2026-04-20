"""
Phone-number normalisation for Iraqi numbers.

Kaasb stores every phone in strict international format: ``+9647XXXXXXXXX``.
Any other shape (``07...``, ``7...``, ``00964...``, spaces, dashes) is
converted before it reaches the database so that login lookups always match.
"""

from __future__ import annotations

import re

_DIGIT_NOISE = re.compile(r"[\s\-()]+")


def normalize_iraqi_phone(raw: str | None) -> str | None:
    """
    Return ``+9647XXXXXXXXX`` for any recognised Iraqi phone shape.

    Accepted inputs (after stripping spaces/dashes/parens):
      ``07XXXXXXXXX``     local 11-digit
      ``7XXXXXXXXX``      local 10-digit (leading zero dropped)
      ``9647XXXXXXXXX``   international w/o plus
      ``009647XXXXXXXXX`` international w/ trunk prefix
      ``+9647XXXXXXXXX``  already normalised

    Anything else — including already-valid non-Iraqi international numbers
    starting with ``+`` — is returned untouched so callers outside Iraq still
    work. Empty / whitespace-only input returns ``None``.
    """
    if raw is None:
        return None

    s = _DIGIT_NOISE.sub("", raw.strip())
    if not s:
        return None

    if s.startswith("00"):
        s = "+" + s[2:]

    if s.startswith("+964") and len(s) == 14 and s[4] == "7":
        return s
    if s.startswith("964") and len(s) == 13 and s[3] == "7":
        return "+" + s
    if s.startswith("07") and len(s) == 11:
        return "+964" + s[1:]
    if s.startswith("7") and len(s) == 10:
        return "+964" + s

    return s
