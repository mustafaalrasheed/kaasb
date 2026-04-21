"""
Kaasb Platform - Models Package
Import all models here so Alembic can discover them.
"""

from app.models.admin_audit import (
    AdminAuditAction,
    AdminAuditLog,
    PayoutApproval,
    PayoutApprovalStatus,
)
from app.models.base import BaseModel
from app.models.buyer_request import (
    BuyerRequest,
    BuyerRequestOffer,
    BuyerRequestOfferStatus,
    BuyerRequestStatus,
)
from app.models.contract import Contract, ContractStatus, Milestone, MilestoneStatus
from app.models.dispute import Dispute, DisputeReason, DisputeStatus
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
from app.models.phone_otp import PhoneOtp
from app.models.proposal import Proposal, ProposalStatus
from app.models.refresh_token import RefreshToken
from app.models.report import Report, ReportReason, ReportStatus, ReportType
from app.models.review import Review
from app.models.service import (
    Service,
    ServiceCategory,
    ServiceOrder,
    ServiceOrderDelivery,
    ServiceOrderStatus,
    ServicePackage,
    ServicePackageTier,
    ServiceStatus,
    ServiceSubcategory,
)
from app.models.user import SellerLevel, User, UserRole, UserStatus
from app.models.violation_log import ViolationAction, ViolationLog, ViolationType

# Legacy aliases — same classes, old names. Removed once all call sites migrate.
Gig = Service
GigOrder = ServiceOrder
GigPackage = ServicePackage
OrderDelivery = ServiceOrderDelivery
Category = ServiceCategory
Subcategory = ServiceSubcategory
GigStatus = ServiceStatus
GigOrderStatus = ServiceOrderStatus
GigPackageTier = ServicePackageTier

__all__ = [
    "BaseModel",
    "AdminAuditLog", "AdminAuditAction", "PayoutApproval", "PayoutApprovalStatus",
    "User", "UserRole", "UserStatus", "SellerLevel",
    "BuyerRequest", "BuyerRequestOffer", "BuyerRequestStatus", "BuyerRequestOfferStatus",
    "Dispute", "DisputeReason", "DisputeStatus",
    "ViolationLog", "ViolationType", "ViolationAction",
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
    "Service", "ServiceStatus", "ServicePackage", "ServicePackageTier",
    "ServiceOrder", "ServiceOrderStatus", "ServiceOrderDelivery",
    "ServiceCategory", "ServiceSubcategory",
    # Legacy aliases — kept until all call sites migrate.
    "Category", "Subcategory",
    "Gig", "GigStatus", "GigPackage", "GigPackageTier",
    "GigOrder", "GigOrderStatus", "OrderDelivery",
]
