"""
Kaasb Platform - Dispute Endpoints (F5)

Authenticated users
  POST   /disputes/orders/{order_id}          Open a dispute on an order
  GET    /disputes/orders/{order_id}          Get dispute for an order

Admin
  GET    /disputes                            List all disputes
  PATCH  /disputes/{dispute_id}/assign        Admin takes ownership
  POST   /disputes/{dispute_id}/resolve       Admin resolves
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_current_user
from app.core.database import get_db
from app.models.dispute import DisputeStatus
from app.models.user import User
from app.schemas.dispute import DisputeAdminAssign, DisputeAdminResolve, DisputeCreate, DisputeOut
from app.services.dispute_service import DisputeService

router = APIRouter(prefix="/disputes", tags=["Disputes"])


@router.post(
    "/orders/{order_id}",
    response_model=DisputeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Open a dispute on an order",
)
async def open_dispute(
    order_id: uuid.UUID,
    data: DisputeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DisputeOut:
    dispute = await DisputeService(db).open_dispute(order_id, current_user, data)
    return DisputeOut.model_validate(dispute)


@router.get(
    "/orders/{order_id}",
    response_model=DisputeOut,
    summary="Get dispute for an order",
)
async def get_dispute(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DisputeOut:
    dispute = await DisputeService(db).get_dispute_by_order(order_id, current_user)
    return DisputeOut.model_validate(dispute)


@router.get(
    "",
    response_model=list[DisputeOut],
    summary="Admin: list all disputes",
)
async def list_disputes(
    status_filter: Optional[str] = Query(None, alias="status"),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[DisputeOut]:
    ds = None
    if status_filter:
        try:
            ds = DisputeStatus(status_filter)
        except ValueError:
            ds = None
    disputes = await DisputeService(db).list_all_disputes(status=ds)
    return [DisputeOut.model_validate(d) for d in disputes]


@router.patch(
    "/{dispute_id}/assign",
    response_model=DisputeOut,
    summary="Admin: assign dispute to self",
)
async def assign_dispute(
    dispute_id: uuid.UUID,
    data: DisputeAdminAssign,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> DisputeOut:
    dispute = await DisputeService(db).assign_admin(dispute_id, admin, notes=data.admin_notes)
    return DisputeOut.model_validate(dispute)


@router.post(
    "/{dispute_id}/resolve",
    response_model=DisputeOut,
    summary="Admin: resolve a dispute (release or refund)",
)
async def resolve_dispute(
    dispute_id: uuid.UUID,
    data: DisputeAdminResolve,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> DisputeOut:
    dispute = await DisputeService(db).resolve_dispute(
        dispute_id, admin, resolution=data.resolution, admin_notes=data.admin_notes
    )
    return DisputeOut.model_validate(dispute)
