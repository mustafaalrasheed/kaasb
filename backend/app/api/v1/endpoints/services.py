"""
Kaasb Platform - Service Endpoints (Fiverr-style marketplace)

Public
  GET    /services                       Browse / search active services
  GET    /services/categories            List all categories with subcategories
  GET    /services/{slug}                Service detail page

Authenticated (freelancers)
  POST   /services                       Create a service (goes to review queue)
  GET    /services/my                    My services
  PUT    /services/{service_id}          Update a service
  DELETE /services/{service_id}          Delete a service (no orders)
  POST   /services/{service_id}/pause    Pause an active service
  POST   /services/{service_id}/resume   Resume a paused service

Orders
  POST   /services/orders                Place an order
  GET    /services/orders/buying         My purchases as client
  GET    /services/orders/selling        My active orders as freelancer
  POST   /services/orders/{id}/deliver   Mark delivered (freelancer)
  POST   /services/orders/{id}/revision  Request revision (client)
  POST   /services/orders/{id}/complete  Complete order (client)

Admin
  GET    /services/admin/pending                    Pending review queue
  POST   /services/admin/{service_id}/approve       Approve service
  POST   /services/admin/{service_id}/reject        Reject service
"""

import uuid

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_admin,
    get_current_user,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.service import (
    CategoryWithSubsOut,
    DeliverBody,
    OrderDeliveryOut,
    ServiceCreate,
    ServiceListItem,
    ServiceOrderCreate,
    ServiceOrderOut,
    ServiceOut,
    ServiceRequirementsSubmit,
    ServiceSearchParams,
    ServiceUpdate,
)
from app.services.catalog_service import CatalogService
from app.utils.files import save_service_image

router = APIRouter(tags=["Services"])


# ──────────────────────────────────────────────
# Public
# ──────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryWithSubsOut], summary="List categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    svc = CatalogService(db)
    cats = await svc.list_categories()
    return cats


@router.get("", response_model=dict, summary="Search services")
async def search_services(
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
    params = ServiceSearchParams(
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
    svc = CatalogService(db)
    services, total = await svc.search_services(params)

    items = []
    for service in services:
        prices = [float(p.price) for p in service.packages] if service.packages else []
        days = [p.delivery_days for p in service.packages] if service.packages else []
        items.append(
            ServiceListItem(
                id=service.id,
                title=service.title,
                slug=service.slug,
                thumbnail_url=service.thumbnail_url,
                avg_rating=float(service.avg_rating),
                reviews_count=service.reviews_count,
                orders_count=service.orders_count,
                min_price=min(prices) if prices else None,
                delivery_days=min(days) if days else None,
                status=service.status,
                freelancer=service.freelancer,
            )
        )

    return {
        "data": [item.model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/my", response_model=list[ServiceOut], summary="My services (freelancer)")
async def list_my_services(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.list_my_services(current_user)


@router.get("/my/{service_id}", response_model=ServiceOut, summary="Get my service by id (any status)")
async def get_my_service(
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.get_service_by_id_for_owner(service_id, current_user)


@router.get("/orders/buying", response_model=list[ServiceOrderOut], summary="Orders I placed as client")
async def my_orders_as_client(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.get_my_orders_as_client(current_user)


@router.get("/orders/selling", response_model=list[ServiceOrderOut], summary="Orders I received as freelancer")
async def my_orders_as_freelancer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.get_my_orders_as_freelancer(current_user)


@router.get("/admin/pending", response_model=list[ServiceOut], summary="Admin: pending services")
async def admin_pending_services(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.list_pending_services()


@router.get("/{slug}", response_model=ServiceOut, summary="Get service by slug")
async def get_service(slug: str, db: AsyncSession = Depends(get_db)):
    svc = CatalogService(db)
    return await svc.get_service_by_slug(slug)


# ──────────────────────────────────────────────
# Authenticated — Service Management
# ──────────────────────────────────────────────

@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED, summary="Create service")
async def create_service(
    data: ServiceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.create_service(current_user, data)


@router.put("/{service_id}", response_model=ServiceOut, summary="Update service")
async def update_service(
    service_id: uuid.UUID,
    data: ServiceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.update_service(service_id, current_user, data)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete service")
async def delete_service(
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    await svc.delete_service(service_id, current_user)


@router.post("/{service_id}/pause", response_model=ServiceOut, summary="Pause service")
async def pause_service(
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.pause_service(service_id, current_user)


@router.post("/{service_id}/resume", response_model=ServiceOut, summary="Resume service")
async def resume_service(
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.resume_service(service_id, current_user)


@router.post("/{service_id}/images", response_model=ServiceOut, summary="Upload a service image (max 5)")
async def upload_service_image(
    service_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    image_url = await save_service_image(file, str(service_id))
    svc = CatalogService(db)
    return await svc.add_image(service_id, current_user, image_url)


@router.delete("/{service_id}/images/{index}", response_model=ServiceOut, summary="Remove a service image by index")
async def delete_service_image_endpoint(
    service_id: uuid.UUID,
    index: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.remove_image(service_id, current_user, index)


# ──────────────────────────────────────────────
# Orders
# ──────────────────────────────────────────────

@router.post(
    "/orders",
    response_model=ServiceOrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Place a service order",
)
async def place_order(
    data: ServiceOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a service order and initiate Qi Card payment.
    The response includes `payment_url` — redirect the client there to complete payment.
    """
    svc = CatalogService(db)
    order, payment_url = await svc.place_order(current_user, data)
    out = ServiceOrderOut.model_validate(order)
    out.payment_url = payment_url
    return out


@router.post(
    "/orders/{order_id}/requirements",
    response_model=ServiceOrderOut,
    summary="Submit requirement answers (client, F3)",
)
async def submit_requirements(
    order_id: uuid.UUID,
    data: ServiceRequirementsSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    answers = [a.model_dump() for a in data.answers]
    return await svc.submit_requirements(order_id, current_user, answers)


@router.post("/orders/{order_id}/deliver", response_model=ServiceOrderOut, summary="Submit delivery (F4)")
async def mark_delivered(
    order_id: uuid.UUID,
    data: DeliverBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.mark_delivered(order_id, current_user, message=data.message, files=data.files)


@router.get(
    "/orders/{order_id}/deliveries",
    response_model=list[OrderDeliveryOut],
    summary="List deliveries for an order (F4)",
)
async def list_deliveries(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.list_deliveries(order_id, current_user)


@router.post("/orders/{order_id}/revision", response_model=ServiceOrderOut, summary="Request revision")
async def request_revision(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.request_revision(order_id, current_user)


@router.post("/orders/{order_id}/complete", response_model=ServiceOrderOut, summary="Complete order")
async def complete_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.complete_order(order_id, current_user)


# ──────────────────────────────────────────────
# Disputes + Admin
# ──────────────────────────────────────────────

@router.post(
    "/orders/{order_id}/dispute",
    response_model=ServiceOrderOut,
    summary="Raise a dispute on an order (client only)",
)
async def raise_dispute(
    order_id: uuid.UUID,
    reason: str = Body(..., min_length=20, max_length=2000, embed=True,
                       description="Detailed reason for the dispute"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Client raises a dispute on an in-progress or delivered order.
    The escrow is frozen and an admin is notified for manual review.
    """
    svc = CatalogService(db)
    return await svc.raise_dispute(order_id, current_user, reason)


@router.get(
    "/admin/disputes",
    response_model=list[ServiceOrderOut],
    summary="Admin: list disputed orders",
)
async def list_disputed_orders(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin view: all orders currently in DISPUTED state."""
    svc = CatalogService(db)
    return await svc.list_disputed_orders()


@router.post(
    "/admin/orders/{order_id}/resolve-dispute",
    response_model=ServiceOrderOut,
    summary="Admin: resolve a disputed order",
)
async def resolve_dispute(
    order_id: uuid.UUID,
    resolution: str = Body(..., pattern="^(release|refund)$", embed=True,
                           description="'release' pays the freelancer, 'refund' returns money to client"),
    admin_note: str = Body("", max_length=1000, embed=True),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin resolves a dispute.
    - resolution=release → pays freelancer, marks order COMPLETED
    - resolution=refund  → refunds client, marks order CANCELLED
    """
    svc = CatalogService(db)
    return await svc.resolve_dispute(order_id, admin, resolution, admin_note)


@router.post("/admin/{service_id}/approve", response_model=ServiceOut, summary="Admin: approve service")
async def approve_service(
    service_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.approve_service(service_id, admin)


@router.post("/admin/{service_id}/request-revision", response_model=ServiceOut, summary="Admin: request revision on service")
async def admin_request_service_revision(
    service_id: uuid.UUID,
    note: str = Query(..., min_length=10, description="Specific feedback for the freelancer"),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.request_service_revision(service_id, note, admin)


@router.post("/admin/{service_id}/reject", response_model=ServiceOut, summary="Admin: reject service")
async def reject_service(
    service_id: uuid.UUID,
    reason: str = Query(..., min_length=10),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = CatalogService(db)
    return await svc.reject_service(service_id, reason, admin)
