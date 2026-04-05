"""
Kaasb Platform - Models Package
Import all models here so Alembic can discover them.
"""

from app.models.base import BaseModel
from app.models.contract import Contract, ContractStatus, Milestone, MilestoneStatus
from app.models.phone_otp import PhoneOtp
from app.models.gig import (
    Category,
    Gig,
    GigOrder,
    GigOrderStatus,
    GigPackage,
    GigPackageTier,
    GigStatus,
    Subcategory,
)
from app.models.job import ExperienceLevel, Job, JobDuration, JobStatus, JobType
from app.models.message import Conversation, Message
from app.models.notification import Notification, NotificationType
from app.models.payment import (
    Escrow,
    EscrowStatus,
    PaymentAccount,
    PaymentAccountStatus,
    PaymentProvider,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.models.proposal import Proposal, ProposalStatus
from app.models.refresh_token import RefreshToken
from app.models.report import Report, ReportReason, ReportStatus, ReportType
from app.models.review import Review
from app.models.user import User, UserRole, UserStatus

__all__ = [
    "BaseModel",
    "User", "UserRole", "UserStatus",
    "PhoneOtp",
    "RefreshToken",
    "Job", "JobStatus", "JobType", "ExperienceLevel", "JobDuration",
    "Proposal", "ProposalStatus",
    "Contract", "ContractStatus", "Milestone", "MilestoneStatus",
    "PaymentAccount", "PaymentAccountStatus", "PaymentProvider",
    "Transaction", "TransactionType", "TransactionStatus",
    "Escrow", "EscrowStatus",
    "Review",
    "Notification", "NotificationType",
    "Conversation", "Message",
    "Report", "ReportType", "ReportReason", "ReportStatus",
    "Category", "Subcategory",
    "Gig", "GigStatus", "GigPackage", "GigPackageTier",
    "GigOrder", "GigOrderStatus",
]
