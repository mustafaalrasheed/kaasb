"""
Kaasb Platform - Payment Endpoints
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
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
from app.services.qi_card_client import QiCardClient, STATUS_SUCCESS, STATUS_FAILED, STATUS_AUTH_FAILED

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


# === Qi Card Webhook (server-to-server, called by Qi Card after payment) ===

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
    Qi Card POSTs here when a payment status changes.
    This endpoint is unauthenticated (called by Qi Card servers, not users).

    Security: We verify the payment by calling GET /payment/{id}/status on the
    Qi Card API before updating our database — never trust webhook payload alone.

    Must return HTTP 200, otherwise Qi Card will retry.
    """
    import json

    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as e:
        logger.error("Qi Card webhook: invalid JSON from %s: %s",
                     request.client.host if request.client else "unknown", e)
        # Return 200 so Qi Card stops retrying a malformed request
        return {"received": False, "error": "invalid_json"}

    try:
        event = QiCardWebhookEvent(**payload)
    except (ValueError, KeyError) as e:
        logger.error("Qi Card webhook: payload schema error: %s | body: %s", e, raw_body[:500])
        return {"received": False, "error": "invalid_payload"}

    logger.info(
        "Qi Card webhook received: payment_id=%s status=%s amount=%s",
        event.payment_id, event.status, event.amount,
    )

    service = PaymentService(db)

    # Always verify status via API before acting (never trust webhook body alone)
    result = await service.verify_and_confirm_qi_card_payment(event.payment_id)
    logger.info("Qi Card webhook processed: payment_id=%s result=%s", event.payment_id, result)

    return {"received": True}


# === Qi Card Payment Return (browser redirect after payment) ===

@router.get(
    "/qi-card/verify",
    summary="Verify Qi Card payment after redirect",
)
async def qi_card_verify(
    payment_id: str = Query(..., description="Qi Card paymentId from redirect URL"),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by the frontend after the user is redirected back from Qi Card's payment page.
    Verifies the payment status with Qi Card and updates the database.

    Frontend usage:
        After redirect to /payment/result?paymentId=xxx, call:
        GET /api/v1/payments/qi-card/verify?payment_id=xxx

    Returns:
        {"status": "SUCCESS"|"FAILED"|"PENDING", "message": "..."}
    """
    if not payment_id or not payment_id.strip():
        raise HTTPException(status_code=400, detail="payment_id is required")

    service = PaymentService(db)
    result = await service.verify_and_confirm_qi_card_payment(payment_id.strip())

    logger.info("Qi Card verify: payment_id=%s result=%s", payment_id, result)
    return result
