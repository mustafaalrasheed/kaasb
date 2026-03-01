"""
Kaasb Platform - Models Package
Import all models here so Alembic can discover them.
"""

from app.models.base import BaseModel
from app.models.user import User, UserRole, UserStatus
from app.models.job import Job, JobStatus, JobType, ExperienceLevel, JobDuration
from app.models.proposal import Proposal, ProposalStatus
from app.models.contract import Contract, ContractStatus, Milestone, MilestoneStatus
from app.models.payment import (
    PaymentAccount, PaymentAccountStatus, PaymentProvider,
    Transaction, TransactionType, TransactionStatus,
    Escrow, EscrowStatus,
)
from app.models.review import Review
from app.models.notification import Notification, NotificationType
from app.models.message import Conversation, Message

__all__ = [
    "BaseModel",
    "User", "UserRole", "UserStatus",
    "Job", "JobStatus", "JobType", "ExperienceLevel", "JobDuration",
    "Proposal", "ProposalStatus",
    "Contract", "ContractStatus", "Milestone", "MilestoneStatus",
    "PaymentAccount", "PaymentAccountStatus", "PaymentProvider",
    "Transaction", "TransactionType", "TransactionStatus",
    "Escrow", "EscrowStatus",
    "Review",
    "Notification", "NotificationType",
    "Conversation", "Message",
]
