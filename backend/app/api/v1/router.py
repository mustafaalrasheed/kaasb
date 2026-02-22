"""
Kaasb Platform - API v1 Router
Aggregates all endpoint routers under /api/v1.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.jobs import router as jobs_router
from app.api.v1.endpoints.proposals import router as proposals_router

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(jobs_router)
api_router.include_router(proposals_router)

# Future routers will be added here:
# api_router.include_router(contracts_router)
# api_router.include_router(messages_router)
# api_router.include_router(payments_router)
# api_router.include_router(reviews_router)
