"""Kaasb Platform - Schemas Package"""

from app.schemas.user import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserProfile,
    UserProfileUpdate,
    UserMe,
    PasswordChange,
    UserListResponse,
)

from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobSummary,
    JobDetail,
    JobListResponse,
    JobClientInfo,
)

from app.schemas.proposal import (
    ProposalCreate,
    ProposalUpdate,
    ProposalRespond,
    ProposalDetail,
    ProposalSummary,
    ProposalListResponse,
    ProposalFreelancerInfo,
    ProposalJobInfo,
)

from app.schemas.contract import (
    ContractCreate,
    ContractDetail,
    ContractSummary,
    ContractListResponse,
    ContractUserInfo,
    ContractJobInfo,
    MilestoneCreate,
    MilestoneUpdate,
    MilestoneSubmit,
    MilestoneReview,
    MilestoneDetail,
)

__all__ = [
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "TokenRefresh",
    "UserProfile",
    "UserProfileUpdate",
    "UserMe",
    "PasswordChange",
    "UserListResponse",
    "JobCreate",
    "JobUpdate",
    "JobSummary",
    "JobDetail",
    "JobListResponse",
    "JobClientInfo",
    "ProposalCreate",
    "ProposalUpdate",
    "ProposalRespond",
    "ProposalDetail",
    "ProposalSummary",
    "ProposalListResponse",
    "ProposalFreelancerInfo",
    "ProposalJobInfo",
    "ContractCreate",
    "ContractDetail",
    "ContractSummary",
    "ContractListResponse",
    "ContractUserInfo",
    "ContractJobInfo",
    "MilestoneCreate",
    "MilestoneUpdate",
    "MilestoneSubmit",
    "MilestoneReview",
    "MilestoneDetail",
]
