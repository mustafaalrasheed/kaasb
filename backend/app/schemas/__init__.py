"""Kaasb Platform - Schemas Package"""
# ruff: noqa: F401  — intentional re-exports

from app.schemas.admin import (
    AdminJobInfo,
    AdminJobListResponse,
    AdminJobStatusUpdate,
    AdminTransactionInfo,
    AdminTransactionListResponse,
    AdminUserInfo,
    AdminUserListResponse,
    AdminUserStatusUpdate,
    PlatformStats,
)
from app.schemas.contract import (
    ContractCreate,
    ContractDetail,
    ContractJobInfo,
    ContractListResponse,
    ContractSummary,
    ContractUserInfo,
    MilestoneCreate,
    MilestoneDetail,
    MilestoneReview,
    MilestoneSubmit,
    MilestoneUpdate,
)
from app.schemas.job import (
    JobClientInfo,
    JobCreate,
    JobDetail,
    JobListResponse,
    JobSummary,
    JobUpdate,
)
from app.schemas.message import (
    ConversationCreate,
    ConversationJobInfo,
    ConversationListResponse,
    ConversationSummary,
    MessageCreate,
    MessageDetail,
    MessageListResponse,
    MessageUserInfo,
)
from app.schemas.notification import (
    NotificationDetail,
    NotificationListResponse,
    NotificationMarkRead,
    UnreadCount,
)
from app.schemas.payment import (
    EscrowFundRequest,
    EscrowFundResponse,
    EscrowReleaseResponse,
    PaymentAccountResponse,
    PaymentAccountSetup,
    PaymentSummary,
    PayoutRequest,
    PayoutResponse,
    TransactionListResponse,
    TransactionResponse,
)
from app.schemas.proposal import (
    ProposalCreate,
    ProposalDetail,
    ProposalFreelancerInfo,
    ProposalJobInfo,
    ProposalListResponse,
    ProposalRespond,
    ProposalSummary,
    ProposalUpdate,
)
from app.schemas.review import (
    ReviewContractInfo,
    ReviewCreate,
    ReviewDetail,
    ReviewListResponse,
    ReviewStats,
    ReviewUserInfo,
)
from app.schemas.user import (
    PasswordChange,
    TokenRefresh,
    TokenResponse,
    UserListResponse,
    UserLogin,
    UserMe,
    UserProfile,
    UserProfileUpdate,
    UserRegister,
)
