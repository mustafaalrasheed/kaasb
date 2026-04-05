"""
Kaasb Platform - Phone OTP Model
Short-lived one-time passwords for phone-based login.
Beta: delivered via email. Production: Twilio SMS.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class PhoneOtp(BaseModel):
    """
    Stores a hashed OTP linked to a phone number.
    Each OTP expires in 10 minutes and is single-use.
    After 5 wrong attempts the record is invalidated.
    """

    __tablename__ = "phone_otps"

    # Phone number exactly as provided (+964XXXXXXXXXX)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # SHA-256 hash of the 6-digit OTP — never store plain OTPs
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Expiry timestamp (UTC)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Marks the OTP as consumed or forcibly expired after too many attempts
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Wrong-attempt counter — record is locked at >= 5
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<PhoneOtp phone={self.phone[-4:]} expires={self.expires_at} used={self.is_used}>"
