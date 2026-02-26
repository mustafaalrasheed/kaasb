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
    PaymentAccount,
    PaymentAccountStatus,
    Transaction,
    TransactionType,
    TransactionStatus,
    Escrow,
    EscrowStatus,
)

__all__ = [
    "BaseModel",
    "User",
    "UserRole",
    "UserStatus",
    "Job",
    "JobStatus",
    "JobType",
    "ExperienceLevel",
    "JobDuration",
    "Proposal",
    "ProposalStatus",
    "Contract",
    "ContractStatus",
    "Milestone",
    "MilestoneStatus",
    "PaymentAccount",
    "PaymentAccountStatus",
    "Transaction",
    "TransactionType",
    "TransactionStatus",
    "Escrow",
    "EscrowStatus",
]
