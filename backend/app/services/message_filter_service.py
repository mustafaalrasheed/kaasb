"""
Kaasb Platform - Message Filter Service (F6)
Scans outgoing chat messages for off-platform contact info.
Called by MessageService before persisting a message.

Violation escalation:
  1st: warning — deliver message with contact info masked, warn sender
  2nd: blocked — message dropped, admin notified
  3rd+: suspended — sender's chat blocked for 24h
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationType
from app.models.user import User
from app.models.violation_log import ViolationAction, ViolationLog, ViolationType

# ── Detection patterns ────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+\s*@\s*[A-Za-z0-9.\-]+\s*\.\s*[A-Za-z]{2,}\b",
    re.IGNORECASE,
)

_PHONE_RE = re.compile(
    r"(?:\+964|00964|0)?[\s\-]?7[3-9]\d[\s\-]?\d{3}[\s\-]?\d{4}"  # Iraqi 07xx
    r"|(?:\+\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4,}"  # international
    r"|\b\d{10,13}\b",
    re.IGNORECASE,
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


def _is_allowed_url(url: str) -> bool:
    """Return True if the URL points to kaasb.com (safe to pass through)."""
    return any(domain in url.lower() for domain in _ALLOWED_DOMAINS)


def detect_violations(content: str) -> list[tuple[ViolationType, str]]:
    """
    Scan content for policy violations.
    Returns a list of (type, matched_text) tuples.
    """
    violations: list[tuple[ViolationType, str]] = []

    for m in _EMAIL_RE.finditer(content):
        violations.append((ViolationType.EMAIL, m.group(0)))

    for m in _PHONE_RE.finditer(content):
        violations.append((ViolationType.PHONE, m.group(0)))

    for m in _URL_RE.finditer(content):
        if not _is_allowed_url(m.group(0)):
            violations.append((ViolationType.URL, m.group(0)))

    for m in _EXTERNAL_APP_RE.finditer(content):
        violations.append((ViolationType.EXTERNAL_APP, m.group(0)))

    return violations


def mask_content(content: str) -> str:
    """Replace detected contact info in content with placeholder text."""
    content = _EMAIL_RE.sub("[معلومات الاتصال محذوفة / contact info removed]", content)
    content = _PHONE_RE.sub("[رقم هاتف محذوف / phone removed]", content)

    def _replace_url(m: re.Match) -> str:
        return m.group(0) if _is_allowed_url(m.group(0)) else "[رابط خارجي محذوف / external link removed]"

    content = _URL_RE.sub(_replace_url, content)
    content = _EXTERNAL_APP_RE.sub("[تطبيق خارجي محذوف / external app removed]", content)
    return content


class MessageFilterService:
    """
    Stateless filter: call `process_message` before persisting.
    Returns (filtered_content, blocked: bool, violation_detected: bool).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_message(
        self,
        sender: User,
        content: str,
        message_id: uuid.UUID | None = None,
    ) -> tuple[str, bool]:
        """
        Check content against policies and update user violation state.

        Returns:
          (processed_content, blocked)

          - processed_content: original or masked content
          - blocked: True means the caller should NOT save/deliver the message
        """
        # Check if sender is currently suspended
        now = datetime.now(UTC)
        if sender.chat_suspended_until and sender.chat_suspended_until > now:
            return content, True  # silently block

        violations = detect_violations(content)
        if not violations:
            return content, False  # clean message

        vtype, detected_text = violations[0]  # primary violation
        count = (sender.chat_violations or 0) + 1
        sender.chat_violations = count

        if count == 1:
            action = ViolationAction.WARNING
            masked = mask_content(content)
            blocked = False
            final_content = masked
        elif count == 2:
            action = ViolationAction.BLOCKED
            blocked = True
            final_content = content  # not delivered, so no masking needed
        else:
            action = ViolationAction.SUSPENDED
            blocked = True
            final_content = content
            sender.chat_suspended_until = now + timedelta(hours=SUSPENSION_HOURS)

        # Log the violation
        log = ViolationLog(
            user_id=sender.id,
            message_id=message_id,
            violation_type=vtype,
            content_detected=detected_text[:500],
            action_taken=action,
        )
        self.db.add(log)
        await self.db.flush()

        # Warn sender
        from app.services.notification_service import notify_background  # noqa: PLC0415
        if action == ViolationAction.WARNING:
            asyncio.create_task(notify_background(
                user_id=sender.id,
                type=NotificationType.CHAT_VIOLATION_WARNING,
                title="تحذير: معلومات اتصال ممنوعة",
                message="تم حذف معلومات اتصال خارجية من رسالتك. الانتهاك التالي سيؤدي لحظر الرسالة.",
                link_type=None,
                link_id=None,
            ))
        elif action == ViolationAction.BLOCKED:
            asyncio.create_task(notify_background(
                user_id=sender.id,
                type=NotificationType.CHAT_VIOLATION_WARNING,
                title="رسالتك تم حجبها",
                message="تم حجب رسالتك لأنها تحتوي على معلومات اتصال خارجية. الانتهاك القادم سيؤدي لتعليق حسابك.",
                link_type=None,
                link_id=None,
            ))
        elif action == ViolationAction.SUSPENDED:
            asyncio.create_task(notify_background(
                user_id=sender.id,
                type=NotificationType.CHAT_VIOLATION_WARNING,
                title="تم تعليق محادثاتك مؤقتاً",
                message=f"تم تعليق إمكانية إرسال الرسائل لمدة {SUSPENSION_HOURS} ساعة بسبب تكرار انتهاك سياسة التواصل خارج المنصة.",
                link_type=None,
                link_id=None,
            ))
            # Notify admins on suspension
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
                    title="مستخدم معلق بسبب انتهاكات المحادثة",
                    message=f"المستخدم {sender.username} تم تعليقه {SUSPENSION_HOURS}h بسبب {count} انتهاكات.",
                    link_type=None,
                    link_id=None,
                    actor_id=sender.id,
                ))

        return final_content, blocked
