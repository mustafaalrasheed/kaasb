"""
Kaasb Platform - Buyer Request Endpoints

Public (authenticated)
  GET    /buyer-requests                    Browse open requests (freelancer view)
  GET    /buyer-requests/my                 Client: my requests
  GET    /buyer-requests/{id}               Get single request

Client
  POST   /buyer-requests                    Create request
  DELETE /buyer-requests/{id}               Cancel request
  GET    /buyer-requests/{id}/offers        Client views offers on their request
  PATCH  /buyer-requests/{id}/offers/{oid}/accept   Accept an offer
  PATCH  /buyer-requests/{id}/offers/{oid}/reject   Reject an offer

Freelancer
  POST   /buyer-requests/{id}/offers        Send an offer
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.buyer_request import (
    BuyerRequestCreate,
    BuyerRequestListOut,
    BuyerRequestOfferCreate,
    BuyerRequestOfferOut,
    BuyerRequestOut,
)
from app.services.buyer_request_service import BuyerRequestService

router = APIRouter(prefix="/buyer-requests", tags=["Buyer Requests"])


@router.post("", response_model=BuyerRequestOut, status_code=status.HTTP_201_CREATED)
async def create_request(
    data: BuyerRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BuyerRequestOut:
    req = await BuyerRequestService(db).create_request(current_user, data)
    return _serialize_request(req)


@router.get("", response_model=BuyerRequestListOut)
async def list_requests(
    category_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BuyerRequestListOut:
    requests, total = await BuyerRequestService(db).list_requests(
        page=page, page_size=page_size, category_id=category_id
    )
    return BuyerRequestListOut(
        items=[_serialize_request(r) for r in requests],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/my", response_model=list[BuyerRequestOut])
async def my_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BuyerRequestOut]:
    requests = await BuyerRequestService(db).my_requests(current_user)
    return [_serialize_request(r) for r in requests]


@router.get("/{request_id}", response_model=BuyerRequestOut)
async def get_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BuyerRequestOut:
    req = await BuyerRequestService(db).get_request(request_id)
    return _serialize_request(req)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await BuyerRequestService(db).cancel_request(request_id, current_user)


@router.post(
    "/{request_id}/offers",
    response_model=BuyerRequestOfferOut,
    status_code=status.HTTP_201_CREATED,
)
async def send_offer(
    request_id: uuid.UUID,
    data: BuyerRequestOfferCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BuyerRequestOfferOut:
    offer = await BuyerRequestService(db).send_offer(request_id, current_user, data)
    return BuyerRequestOfferOut.model_validate(offer)


@router.get("/{request_id}/offers", response_model=list[BuyerRequestOfferOut])
async def list_offers(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BuyerRequestOfferOut]:
    offers = await BuyerRequestService(db).list_offers_for_request(request_id, current_user)
    return [BuyerRequestOfferOut.model_validate(o) for o in offers]


@router.patch("/{request_id}/offers/{offer_id}/accept", response_model=BuyerRequestOfferOut)
async def accept_offer(
    request_id: uuid.UUID,
    offer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BuyerRequestOfferOut:
    offer = await BuyerRequestService(db).accept_offer(request_id, offer_id, current_user)
    return BuyerRequestOfferOut.model_validate(offer)


@router.patch("/{request_id}/offers/{offer_id}/reject", response_model=BuyerRequestOfferOut)
async def reject_offer(
    request_id: uuid.UUID,
    offer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BuyerRequestOfferOut:
    offer = await BuyerRequestService(db).reject_offer(request_id, offer_id, current_user)
    return BuyerRequestOfferOut.model_validate(offer)


# ──────────────────────────────────────────
# Serialization helpers
# ──────────────────────────────────────────

def _serialize_request(req: object) -> BuyerRequestOut:
    """Convert ORM object to BuyerRequestOut, adding computed offer_count."""
    from app.models.buyer_request import BuyerRequest as BRModel
    r: BRModel = req  # type: ignore[assignment]
    # offers relationship is eagerly loaded via _load_request
    try:
        offer_count = len(r.offers)
    except Exception:
        offer_count = 0
    data = BuyerRequestOut.model_validate(r)
    data.offer_count = offer_count
    return data
