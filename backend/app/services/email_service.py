"""
Kaasb Platform - Email Service (Resend)
Handles all transactional email sending with Jinja2 templates.
Dev mode: logs to console when RESEND_API_KEY is not set.

Deliverability hardening (2026-04-23):
  * The brand wordmark is attached inline via a Content-ID ("cid:kaasb-logo")
    rather than fetched from https://kaasb.com/… at render time. Gmail and
    Outlook proxy or outright block remote <img> on the first email from a
    sender, so a remote logo means "broken first impression" on verification
    / OTP / password-reset. CID attachments render unconditionally.
  * CSS in <style> blocks is inlined on each send via premailer. Outlook
    desktop strips <style> by default, which would otherwise collapse the
    header border, button, and footer to browser defaults.
"""

import base64
import logging
from pathlib import Path
from typing import Literal

import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape
from premailer import transform as _premail_transform

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "emails"
_LOGO_PATH = _TEMPLATE_DIR / "assets" / "logo-wordmark.png"
_LOGO_CID = "kaasb-logo"


class EmailService:
    """Provider-abstracted email service using Resend."""

    def __init__(self) -> None:
        self._settings = get_settings()
        if self._settings.RESEND_API_KEY.strip():
            resend.api_key = self._settings.RESEND_API_KEY.strip()

        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )

        # Read the logo once at startup — ~12 KB; attaching it on every send
        # without re-reading disk. If the file is missing we fall back to the
        # remote URL so emails still ship (degraded brand, but functional).
        self._logo_bytes: bytes | None = None
        self._logo_b64: str | None = None
        try:
            self._logo_bytes = _LOGO_PATH.read_bytes()
            self._logo_b64 = base64.b64encode(self._logo_bytes).decode("ascii")
        except FileNotFoundError:
            logger.warning(
                "Email logo asset missing at %s — emails will reference the "
                "remote URL instead. Verify the brand asset is shipped with "
                "the backend image.", _LOGO_PATH,
            )

    def _render(self, template: str, ctx: dict) -> str:
        html = self._env.get_template(template).render(**ctx)

        # If the logo file is missing, rewrite the CID reference back to the
        # remote URL so we don't serve a broken <img src="cid:kaasb-logo">
        # with no matching attachment.
        if self._logo_bytes is None:
            html = html.replace(
                f"cid:{_LOGO_CID}",
                "https://kaasb.com/logo-wordmark.png",
            )

        # Inline <style> rules onto elements so Outlook desktop renders the
        # header divider, button, and footer the same way Gmail and Apple
        # Mail do. `keep_style_tags=True` leaves the original <style> block
        # intact as a fallback for clients that *do* honour it.
        try:
            return _premail_transform(
                html,
                keep_style_tags=True,
                cssutils_logging_level=logging.CRITICAL,  # silence noisy warnings
                disable_validation=True,
            )
        except Exception as exc:
            # Premailer failures must never block an OTP or password-reset
            # email — fall back to the un-inlined HTML. Clients that honour
            # <style> render correctly; Outlook sees the reduced layout.
            logger.warning(
                "Premailer failed for template %s, sending un-inlined: %s",
                template, exc,
            )
            return html

    async def _send(self, *, to: str, subject: str, html: str) -> bool:
        if not self._settings.RESEND_API_KEY.strip():
            logger.info("[EMAIL DEV] To=%s | Subject=%s", to, subject)
            return True
        payload: dict = {
            "from": self._settings.EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if self._logo_b64 is not None:
            # Resend's attachment contract: `content_id` makes the attachment
            # inline (referenced from the HTML as `cid:<value>`) rather than
            # a downloadable attachment in the client UI.
            payload["attachments"] = [
                {
                    "filename": "logo-wordmark.png",
                    "content": self._logo_b64,
                    "content_type": "image/png",
                    "content_id": _LOGO_CID,
                }
            ]
        try:
            resend.Emails.send(payload)
            return True
        except Exception as exc:
            logger.error("Email send failed to %s: %s", to, exc)
            return False

    # ── Public Methods ──────────────────────────────────────────────────────

    async def send_verification_email(
        self,
        *,
        to_email: str,
        user_name: str,
        token: str,
        lang: Literal["ar", "en"] = "ar",
    ) -> bool:
        base = self._settings.FRONTEND_URL
        url = f"{base}/auth/verify-email?token={token}"
        ctx = {"user_name": user_name, "verification_url": url, "site_name": "Kaasb"}
        template = f"verify_email_{lang}.html"
        subject = "تأكيد بريدك الإلكتروني | Kaasb" if lang == "ar" else "Verify your email | Kaasb"
        html = self._render(template, ctx)
        return await self._send(to=to_email, subject=subject, html=html)

    async def send_password_reset(
        self,
        *,
        to_email: str,
        user_name: str,
        token: str,
        lang: Literal["ar", "en"] = "ar",
    ) -> bool:
        base = self._settings.FRONTEND_URL
        url = f"{base}/auth/reset-password?token={token}"
        ctx = {"user_name": user_name, "reset_url": url, "site_name": "Kaasb"}
        template = f"reset_password_{lang}.html"
        subject = "إعادة تعيين كلمة المرور | Kaasb" if lang == "ar" else "Reset your password | Kaasb"
        html = self._render(template, ctx)
        return await self._send(to=to_email, subject=subject, html=html)

    async def send_welcome_email(
        self,
        *,
        to_email: str,
        user_name: str,
        lang: Literal["ar", "en"] = "ar",
    ) -> bool:
        ctx = {
            "user_name": user_name,
            "site_name": "Kaasb",
            "dashboard_url": f"{self._settings.FRONTEND_URL}/dashboard",
        }
        template = f"welcome_{lang}.html"
        subject = "مرحباً بك في كاسب | Kaasb" if lang == "ar" else "Welcome to Kaasb!"
        html = self._render(template, ctx)
        return await self._send(to=to_email, subject=subject, html=html)

    async def send_phone_otp(
        self,
        *,
        to_email: str,
        otp_code: str,
        phone: str,
        lang: Literal["ar", "en"] = "ar",
    ) -> bool:
        masked_phone = phone[-4:].zfill(4)
        ctx = {
            "otp_code": otp_code,
            "masked_phone": masked_phone,
            "site_name": "Kaasb",
            "expiry_minutes": 10,
        }
        template = f"phone_otp_{lang}.html"
        subject = f"رمز التحقق: {otp_code} | Kaasb" if lang == "ar" else f"Your OTP: {otp_code} | Kaasb"
        html = self._render(template, ctx)
        return await self._send(to=to_email, subject=subject, html=html)

    async def send_order_placed(
        self,
        *,
        to_email: str,
        user_name: str,
        order_title: str,
        order_url: str,
        lang: Literal["ar", "en"] = "ar",
    ) -> bool:
        ctx = {
            "user_name": user_name,
            "order_title": order_title,
            "order_url": order_url,
            "site_name": "Kaasb",
        }
        template = f"order_placed_{lang}.html"
        subject = f"طلب جديد: {order_title} | Kaasb" if lang == "ar" else f"New order: {order_title} | Kaasb"
        html = self._render(template, ctx)
        return await self._send(to=to_email, subject=subject, html=html)

    async def send_notification_email(
        self,
        *,
        to_email: str,
        title: str,
        message: str,
        link_url: str | None = None,
        lang: Literal["ar", "en"] = "ar",
    ) -> bool:
        """Generic notification email. Called from NotificationService for the
        opted-in notification types. The title/message arguments are expected
        to already be in the recipient's preferred language (the notification
        service resolves locale before calling this)."""
        ctx = {
            "title": title,
            "message": message,
            "link_url": link_url,
            "site_name": "Kaasb",
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
        }
        template = f"notification_{lang}.html"
        subject = f"{title} | Kaasb"
        html = self._render(template, ctx)
        return await self._send(to=to_email, subject=subject, html=html)
