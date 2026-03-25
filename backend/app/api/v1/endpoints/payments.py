"""
Kaasb Platform - Payment Endpoints
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client, get_current_freelancer, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.payment import (
    EscrowFundRequest,
    EscrowFundResponse,
    PaymentAccountResponse,
    PaymentAccountSetup,
    PaymentSummary,
    PayoutRequest,
    PayoutResponse,
    QiCardWebhookEvent,
    TransactionListResponse,
)
from app.services.payment_service import PaymentService
from app.services.qi_card_client import QiCardClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])


# === Static routes first ===

@router.get(
    "/summary",
    response_model=PaymentSummary,
    summary="Get payment dashboard summary",
)
async def get_payment_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment overview: earnings, spending, escrow balance, accounts."""
    service = PaymentService(db)
    return await service.get_payment_summary(current_user)


@router.get(
    "/accounts",
    response_model=list[PaymentAccountResponse],
    summary="List payment accounts",
)
async def list_payment_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all payment accounts for the current user."""
    service = PaymentService(db)
    return await service.get_payment_accounts(current_user)


@router.post(
    "/accounts",
    response_model=PaymentAccountResponse,
    summary="Setup payment account",
    status_code=201,
)
async def setup_payment_account(
    data: PaymentAccountSetup,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set up a Qi Card (or Stripe/Wise) payment account."""
    service = PaymentService(db)
    return await service.setup_payment_account(current_user, data)


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    summary="List transactions",
)
async def list_transactions(
    type: str | None = Query(None, description="Filter: escrow_fund|escrow_release|platform_fee|payout"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get transaction history."""
    service = PaymentService(db)
    return await service.get_transactions(
        user=current_user,
        transaction_type=type,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/escrow/fund",
    response_model=EscrowFundResponse,
    summary="Fund milestone escrow",
    status_code=201,
)
async def fund_escrow(
    data: EscrowFundRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """
    Client initiates escrow funding for a milestone via Qi Card.

    Returns a `payment_redirect_url` — redirect the client there to complete
    the Qi Card payment. Escrow will be marked FUNDED after Qi Card confirms
    via webhook.
    """
    service = PaymentService(db)
    return await service.fund_escrow(current_user, data)


@router.post(
    "/payout",
    response_model=PayoutResponse,
    summary="Request payout",
    status_code=201,
)
async def request_payout(
    data: PayoutRequest,
    current_user: User = Depends(get_current_freelancer),
    db: AsyncSession = Depends(get_db),
):
    """Freelancer requests a payout to their Qi Card account."""
    service = PaymentService(db)
    return await service.request_payout(current_user, data)


# === Qi Card Webhook ===

@router.post(
    "/qi-card/webhook",
    summary="Qi Card payment webhook",
    status_code=200,
)
async def qi_card_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Qi Card calls this endpoint after a payment is completed, failed, or cancelled.

    Security: HMAC-SHA256 signature verified via X-QiCard-Signature header.
    This endpoint is unauthenticated (called by Qi Card servers, not clients).
    """
    raw_body = await request.body()
    signature = request.headers.get("X-QiCard-Signature", "")

    # Verify webhook signature
    qi_client = QiCardClient()
    if not qi_client.verify_webhook_signature(raw_body, signature):
        logger.warning(
            "Qi Card webhook: invalid signature from %s",
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    import json
    try:
        payload = json.loads(raw_body)
        event = QiCardWebhookEvent(**payload)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error("Qi Card webhook: failed to parse payload: %s", e)
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from e

    service = PaymentService(db)

    if event.status == "completed":
        success = await service.confirm_qi_card_payment(
            qi_payment_id=event.payment_id,
            order_id=event.order_id,
        )
        if not success:
            logger.warning("Qi Card webhook: could not confirm payment_id=%s", event.payment_id)
        else:
            logger.info("Qi Card webhook: payment confirmed payment_id=%s", event.payment_id)

    elif event.status in ("failed", "cancelled"):
        await service.handle_qi_card_payment_failed(qi_payment_id=event.payment_id)
        logger.info("Qi Card webhook: payment %s payment_id=%s", event.status, event.payment_id)

    else:
        logger.info("Qi Card webhook: unhandled status=%s payment_id=%s", event.status, event.payment_id)

    # Always return 200 so Qi Card doesn't retry
    return {"received": True}
