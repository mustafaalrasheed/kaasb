"""
Kaasb Platform - Gig Endpoints (Fiverr-style marketplace)

Public
  GET    /gigs                       Browse / search active gigs
  GET    /gigs/categories            List all categories with subcategories
  GET    /gigs/{slug}                Gig detail page

Authenticated (freelancers)
  POST   /gigs                       Create a gig (goes to review queue)
  GET    /gigs/my                    My gigs
  PUT    /gigs/{gig_id}              Update a gig
  DELETE /gigs/{gig_id}              Delete a gig (no orders)
  POST   /gigs/{gig_id}/pause        Pause an active gig
  POST   /gigs/{gig_id}/resume       Resume a paused gig

Orders
  POST   /gigs/orders                Place an order
  GET    /gigs/orders/buying         My purchases as client
  GET    /gigs/orders/selling        My active orders as freelancer
  POST   /gigs/orders/{id}/deliver   Mark delivered (freelancer)
  POST   /gigs/orders/{id}/revision  Request revision (client)
  POST   /gigs/orders/{id}/complete  Complete order (client)

Admin
  GET    /gigs/admin/pending         Pending review queue
  POST   /gigs/admin/{gig_id}/approve  Approve gig
  POST   /gigs/admin/{gig_id}/reject   Reject gig
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_admin,
    get_current_user,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.gig import (
    CategoryWithSubsOut,
    GigCreate,
    GigListItem,
    GigOrderCreate,
    GigOrderOut,
    GigOut,
    GigSearchParams,
    GigUpdate,
)
from app.services.gig_service import GigService

router = APIRouter(prefix="/gigs", tags=["Gigs"])


# ──────────────────────────────────────────────
# Public
# ──────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryWithSubsOut], summary="List categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    svc = GigService(db)
    cats = await svc.list_categories()
    return cats


@router.get("", response_model=dict, summary="Search gigs")
async def search_gigs(
    q: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    subcategory_id: uuid.UUID | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    delivery_days: int | None = Query(None, ge=1),
    sort_by: str = Query("orders", pattern="^(relevance|newest|rating|orders)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    params = GigSearchParams(
        q=q,
        category_id=category_id,
        subcategory_id=subcategory_id,
        min_price=min_price,
        max_price=max_price,
        delivery_days=delivery_days,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    svc = GigService(db)
    gigs, total = await svc.search_gigs(params)

    # Build lightweight list items
    items = []
    for gig in gigs:
        prices = [float(p.price) for p in gig.packages] if gig.packages else []
        days = [p.delivery_days for p in gig.packages] if gig.packages else []
        items.append(
            GigListItem(
                id=gig.id,
                title=gig.title,
                slug=gig.slug,
                thumbnail_url=gig.thumbnail_url,
                avg_rating=float(gig.avg_rating),
                reviews_count=gig.reviews_count,
                orders_count=gig.orders_count,
                min_price=min(prices) if prices else None,
                delivery_days=min(days) if days else None,
                status=gig.status,
                freelancer=gig.freelancer,
            )
        )

    return {
        "data": [item.model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/my", response_model=list[GigOut], summary="My gigs (freelancer)")
async def list_my_gigs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.list_my_gigs(current_user)


@router.get("/orders/buying", response_model=list[GigOrderOut], summary="Orders I placed as client")
async def my_orders_as_client(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.get_my_orders_as_client(current_user)


@router.get("/orders/selling", response_model=list[GigOrderOut], summary="Orders I received as freelancer")
async def my_orders_as_freelancer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.get_my_orders_as_freelancer(current_user)


@router.get("/admin/pending", response_model=list[GigOut], summary="Admin: pending gigs")
async def admin_pending_gigs(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.list_pending_gigs()


@router.get("/{slug}", response_model=GigOut, summary="Get gig by slug")
async def get_gig(slug: str, db: AsyncSession = Depends(get_db)):
    svc = GigService(db)
    return await svc.get_gig_by_slug(slug)


# ──────────────────────────────────────────────
# Authenticated — Gig Management
# ──────────────────────────────────────────────

@router.post("", response_model=GigOut, status_code=status.HTTP_201_CREATED, summary="Create gig")
async def create_gig(
    data: GigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.create_gig(current_user, data)


@router.put("/{gig_id}", response_model=GigOut, summary="Update gig")
async def update_gig(
    gig_id: uuid.UUID,
    data: GigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.update_gig(gig_id, current_user, data)


@router.delete("/{gig_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete gig")
async def delete_gig(
    gig_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    await svc.delete_gig(gig_id, current_user)


@router.post("/{gig_id}/pause", response_model=GigOut, summary="Pause gig")
async def pause_gig(
    gig_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.pause_gig(gig_id, current_user)


@router.post("/{gig_id}/resume", response_model=GigOut, summary="Resume gig")
async def resume_gig(
    gig_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.resume_gig(gig_id, current_user)


# ──────────────────────────────────────────────
# Orders
# ──────────────────────────────────────────────

@router.post(
    "/orders",
    response_model=GigOrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Place a gig order",
)
async def place_order(
    data: GigOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.place_order(current_user, data)


@router.post("/orders/{order_id}/deliver", response_model=GigOrderOut, summary="Mark order as delivered")
async def mark_delivered(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.mark_delivered(order_id, current_user)


@router.post("/orders/{order_id}/revision", response_model=GigOrderOut, summary="Request revision")
async def request_revision(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.request_revision(order_id, current_user)


@router.post("/orders/{order_id}/complete", response_model=GigOrderOut, summary="Complete order")
async def complete_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.complete_order(order_id, current_user)


# ──────────────────────────────────────────────
# Admin
# ──────────────────────────────────────────────

@router.post("/admin/{gig_id}/approve", response_model=GigOut, summary="Admin: approve gig")
async def approve_gig(
    gig_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.approve_gig(gig_id, admin)


@router.post("/admin/{gig_id}/request-revision", response_model=GigOut, summary="Admin: request revision on gig")
async def admin_request_gig_revision(
    gig_id: uuid.UUID,
    note: str = Query(..., min_length=10, description="Specific feedback for the freelancer"),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.request_gig_revision(gig_id, note, admin)


@router.post("/admin/{gig_id}/reject", response_model=GigOut, summary="Admin: reject gig")
async def reject_gig(
    gig_id: uuid.UUID,
    reason: str = Query(..., min_length=10),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = GigService(db)
    return await svc.reject_gig(gig_id, reason, admin)
