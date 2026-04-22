"""
Kaasb Platform - Message Filter Service (F6)
Scans outgoing chat messages for off-platform contact info.
Called by MessageService before persisting a message.

Violation escalation:
  1st: warning — deliver message with contact info masked, warn sender
  2nd: blocked — message dropped, admin notified
  3rd+: suspended — sender's chat blocked for 24h

URL detection is bypassed for ORDER-type conversations so the client and
freelancer can legitimately share deliverable links (Google Drive, GitHub,
portfolio pages, …). Email / phone / external-app patterns stay on — those
are almost always attempts to move off-platform.

Hardening (PR-C1):
  - All input is NFKC-normalised and stripped of zero-width chars before
    regex scanning, so homograph (tеlegram with Cyrillic е) and
    invisible-character (ZWSP inside whatsapp) evasions can't bypass it.
  - Phone detection is Iraqi-specific + explicitly-international (`+`
    prefix required). The old `\\b\\d{10,13}\\b` fallback was dropped —
    it flagged credit cards, order IDs, and large IQD amounts as phones.
  - URL allow-listing uses `urllib.parse.urlparse` + exact-host match.
    The previous substring match treated `fakekaasb.com` and
    `kaasb.com@attacker.com` as allowed.
"""

from __future__ import annotations

import asyncio
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import ConversationType
from app.models.notification import NotificationType
from app.models.user import User
from app.models.violation_log import ViolationAction, ViolationLog, ViolationType

# ── Input normalization ───────────────────────────────────────────────────────

# Zero-width / bidi / BOM characters — stripped before regex matching so a
# sender can't split "telegram" with invisible chars to bypass detection.
_ZERO_WIDTH_RE = re.compile(
    r"[​-‏‪-‮⁠﻿]"
)


def _normalize(text: str) -> str:
    """NFKC-fold and strip zero-width / bidi overrides.

    NFKC collapses Unicode compatibility characters (fullwidth letters,
    ligatures) to their ASCII/canonical equivalents, which also catches
    many Cyrillic-Latin homograph swaps after case-folding.
    """
    return _ZERO_WIDTH_RE.sub("", unicodedata.normalize("NFKC", text))


# ── Detection patterns (all applied to normalized text) ───────────────────────

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+\s*@\s*[A-Za-z0-9.\-]+\s*\.\s*[A-Za-z]{2,}\b",
    re.IGNORECASE,
)

# Iraqi mobile: (+964 | 00964 | 0) followed by 7[3-9] and 8 more digits,
# tolerant of spaces/dashes inside. Anchored so a bare 11-digit sequence
# without a known prefix is NOT matched here (that's the credit-card
# false-positive source we removed).
_PHONE_IRAQI_RE = re.compile(
    r"(?:\+964|00964|0)[\s\-]?7[3-9]\d(?:[\s\-]?\d){7}",
)

# Explicit international phone: requires leading `+`, allows country code
# 1-3 digits, total 7-14 digit body (typical E.164 range). The leading `+`
# requirement prevents "1234567890123" (13 digits, no plus) from matching.
# Parentheses are allowed as digit separators so "+1 (555) 123-4567" matches.
_PHONE_INTL_RE = re.compile(
    # The `*` on the separator class lets " (" or ") " (two separator chars
    # between digits) match, which is what e.g. "+1 (555) 123-4567" needs.
    r"(?<!\d)\+\d{1,3}(?:[\s\-()]*\d){6,13}",
)

_URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s]{3,}|[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}/[^\s]*",
    re.IGNORECASE,
)

_ALLOWED_DOMAINS = {"kaasb.com"}

_EXTERNAL_APP_RE = re.compile(
    r"\bwhatsapp\b|\bواتساب\b|\btelegram\b|\bتلغرام\b|\bviber\b|\bسكايب\b|\bskype\b"
    r"|\bline\b|\bsignal\b|\bweChat\b|\bwechat\b",
    re.IGNORECASE,
)

SUSPENSION_HOURS = 24


@dataclass(frozen=True)
class FilterOutcome:
    """Result of running a message through the off-platform-contact filter.

    ``blocked`` → caller must NOT persist/deliver the message.
    ``warning`` → message WILL be delivered but with contact info masked; UI
                  should surface the escalation notice to the sender.
    ``code``    → stable machine-readable reason ("email" / "phone" / "url" /
                  "external_app" / "suspended") for the frontend to render a
                  targeted message.
    """

    content: str
    blocked: bool
    warning: bool = False
    code: str | None = None
    total_violations: int = 0
    suspended_until: datetime | None = None


def _is_allowed_url(url: str) -> bool:
    """Return True when the URL's host exactly matches an allowed domain
    or is a subdomain of one.

    Uses `urlparse` + `hostname` so userinfo (`http://kaasb.com@evil.com`)
    and arbitrary port suffixes don't trick the check. Substring matching
    (the old implementation) would pass `fakekaasb.com`,
    `kaasb.com.phishing.io`, and `http://kaasb.com@attacker.com`.
    """
    # urlparse requires a scheme to populate netloc/hostname. Bare hosts
    # (www.kaasb.com/path) get a synthetic scheme so the parser does the
    # right thing — the returned hostname is what matters.
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return False
    return host in _ALLOWED_DOMAINS or any(
        host.endswith(f".{d}") for d in _ALLOWED_DOMAINS
    )


def detect_violations(
    content: str, *, skip_urls: bool = False,
) -> list[tuple[ViolationType, str]]:
    """Scan normalized content for policy violations.

    Returns a list of (type, matched_text) tuples. Input is normalized up
    front so all downstream matching runs on canonicalised text (NFKC +
    zero-width strip), defeating homoglyph / invisible-char evasions.
    When ``skip_urls`` is True the URL pattern is not evaluated — used for
    ORDER conversations where sharing deliverable links is legitimate.
    """
    content = _normalize(content)
    violations: list[tuple[ViolationType, str]] = []

    for m in _EMAIL_RE.finditer(content):
        violations.append((ViolationType.EMAIL, m.group(0)))

    for m in _PHONE_IRAQI_RE.finditer(content):
        violations.append((ViolationType.PHONE, m.group(0)))
    for m in _PHONE_INTL_RE.finditer(content):
        violations.append((ViolationType.PHONE, m.group(0)))

    if not skip_urls:
        for m in _URL_RE.finditer(content):
            if not _is_allowed_url(m.group(0)):
                violations.append((ViolationType.URL, m.group(0)))

    for m in _EXTERNAL_APP_RE.finditer(content):
        violations.append((ViolationType.EXTERNAL_APP, m.group(0)))

    return violations


def mask_content(content: str, *, skip_urls: bool = False) -> str:
    """Replace detected contact info in content with placeholder text.

    Normalises first so the returned message carries canonicalised chars —
    otherwise a sender could sneak a zero-width character past the filter
    and back into the stored message body.
    """
    content = _normalize(content)
    content = _EMAIL_RE.sub("[معلومات الاتصال محذوفة / contact info removed]", content)
    content = _PHONE_IRAQI_RE.sub("[رقم هاتف محذوف / phone removed]", content)
    content = _PHONE_INTL_RE.sub("[رقم هاتف محذوف / phone removed]", content)

    if not skip_urls:
        def _replace_url(m: re.Match) -> str:
            return m.group(0) if _is_allowed_url(m.group(0)) else "[رابط خارجي محذوف / external link removed]"
        content = _URL_RE.sub(_replace_url, content)

    content = _EXTERNAL_APP_RE.sub("[تطبيق خارجي محذوف / external app removed]", content)
    return content


class MessageFilterService:
    """
    Stateless filter: call `process_message` before persisting.
    Returns a ``FilterOutcome`` — see its docstring.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_message(
        self,
        sender: User,
        content: str,
        *,
        conversation_type: ConversationType = ConversationType.USER,
        message_id: uuid.UUID | None = None,
    ) -> FilterOutcome:
        """Check content against policies and update user violation state.

        Returns a :class:`FilterOutcome` describing whether to block, mask,
        or pass through. The caller MUST honour ``outcome.blocked`` and
        surface ``outcome.code`` / ``outcome.suspended_until`` to the user
        for suspended / blocked cases.
        """
        # Check if sender is currently suspended. The `> now` comparison lets
        # the suspension lift naturally once `chat_suspended_until` is in the
        # past — no explicit column reset is needed.
        now = datetime.now(UTC)

        # Already suspended — short-circuit. Caller raises BadRequest with
        # suspended_until so the UI can show a countdown.
        if sender.chat_suspended_until and sender.chat_suspended_until > now:
            return FilterOutcome(
                content=content,
                blocked=True,
                code="suspended",
                total_violations=sender.chat_violations or 0,
                suspended_until=sender.chat_suspended_until,
            )

        skip_urls = conversation_type == ConversationType.ORDER
        violations = detect_violations(content, skip_urls=skip_urls)
        if not violations:
            # Even on a clean message we return the normalized form so a
            # sneaked zero-width char doesn't survive in the DB.
            return FilterOutcome(content=_normalize(content), blocked=False)

        vtype, detected_text = violations[0]  # primary violation
        count = (sender.chat_violations or 0) + 1
        sender.chat_violations = count

        if count == 1:
            action = ViolationAction.WARNING
            masked = mask_content(content, skip_urls=skip_urls)
            outcome = FilterOutcome(
                content=masked,
                blocked=False,
                warning=True,
                code=vtype.value,
                total_violations=count,
            )
        elif count == 2:
            action = ViolationAction.BLOCKED
            outcome = FilterOutcome(
                content=content,
                blocked=True,
                code=vtype.value,
                total_violations=count,
            )
        else:
            action = ViolationAction.SUSPENDED
            sender.chat_suspended_until = now + timedelta(hours=SUSPENSION_HOURS)
            outcome = FilterOutcome(
                content=content,
                blocked=True,
                code="suspended",
                total_violations=count,
                suspended_until=sender.chat_suspended_until,
            )

        log = ViolationLog(
            user_id=sender.id,
            message_id=message_id,
            violation_type=vtype,
            content_detected=detected_text[:500],
            action_taken=action,
        )
        self.db.add(log)
        await self.db.flush()

        from app.services.notification_service import notify_background  # noqa: PLC0415
        if action == ViolationAction.WARNING:
            asyncio.create_task(notify_background(
                user_id=sender.id,
                type=NotificationType.CHAT_VIOLATION_WARNING,
                title_ar="تحذير: معلومات اتصال ممنوعة",
                title_en="Warning: contact details not allowed",
                message_ar="تم حذف معلومات اتصال خارجية من رسالتك. الانتهاك التالي سيؤدي لحظر الرسالة.",
                message_en="External contact info was removed from your message. The next violation will block the message.",
                link_type=None,
                link_id=None,
            ))
        elif action == ViolationAction.BLOCKED:
            asyncio.create_task(notify_background(
                user_id=sender.id,
                type=NotificationType.CHAT_VIOLATION_WARNING,
                title_ar="رسالتك تم حجبها",
                title_en="Your message was blocked",
                message_ar="تم حجب رسالتك لأنها تحتوي على معلومات اتصال خارجية. الانتهاك القادم سيؤدي لتعليق حسابك.",
                message_en="Your message was blocked for containing external contact info. A further violation will suspend your account.",
                link_type=None,
                link_id=None,
            ))
        elif action == ViolationAction.SUSPENDED:
            asyncio.create_task(notify_background(
                user_id=sender.id,
                type=NotificationType.CHAT_VIOLATION_WARNING,
                title_ar="تم تعليق محادثاتك مؤقتاً",
                title_en="Your messaging is temporarily suspended",
                message_ar=f"تم تعليق إمكانية إرسال الرسائل لمدة {SUSPENSION_HOURS} ساعة بسبب تكرار انتهاك سياسة التواصل خارج المنصة.",
                message_en=f"Messaging is suspended for {SUSPENSION_HOURS}h for repeated off-platform contact violations.",
                link_type=None,
                link_id=None,
            ))
            from app.models.user import UserStatus  # noqa: PLC0415
            admin_result = await self.db.execute(
                select(User).where(
                    User.is_superuser == True,  # noqa: E712
                    User.status == UserStatus.ACTIVE,
                )
            )
            for admin in admin_result.scalars().all():
                asyncio.create_task(notify_background(
                    user_id=admin.id,
                    type=NotificationType.SYSTEM_ALERT,
                    title_ar="مستخدم معلق بسبب انتهاكات المحادثة",
                    title_en="User suspended for chat violations",
                    message_ar=f"المستخدم {sender.username} تم تعليقه {SUSPENSION_HOURS}h بسبب {count} انتهاكات.",
                    message_en=f"User {sender.username} suspended for {SUSPENSION_HOURS}h after {count} violations.",
                    link_type=None,
                    link_id=None,
                    actor_id=sender.id,
                ))

        return outcome
