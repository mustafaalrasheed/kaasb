"""
Kaasb Platform - Email Service (Resend)
Handles all transactional email sending with Jinja2 templates.
Dev mode: logs to console when RESEND_API_KEY is not set.
"""

import logging
from pathlib import Path
from typing import Literal

import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Provider-abstracted email service using Resend."""

    def __init__(self) -> None:
        self._settings = get_settings()
        if self._settings.RESEND_API_KEY:
            resend.api_key = self._settings.RESEND_API_KEY

        template_dir = Path(__file__).parent.parent / "templates" / "emails"
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html"]),
        )

    def _render(self, template: str, ctx: dict) -> str:
        return self._env.get_template(template).render(**ctx)

    async def _send(self, *, to: str, subject: str, html: str) -> bool:
        if not self._settings.RESEND_API_KEY:
            logger.info("[EMAIL DEV] To=%s | Subject=%s", to, subject)
            return True
        try:
            resend.Emails.send(
                {
                    "from": self._settings.EMAIL_FROM,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                }
            )
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
