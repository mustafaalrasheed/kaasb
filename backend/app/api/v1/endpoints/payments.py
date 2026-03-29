"""
Kaasb Platform - Payment Endpoints
"""

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client, get_current_freelancer, get_current_user
from app.core.config import get_settings
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
    TransactionListResponse,
)
from app.services.payment_service import PaymentService

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


# === Qi Card Redirect Handlers ===
# Qi Card redirects the user's browser to these URLs after payment.
# CartID query param contains our order_id ("escrow-<milestone_id>").

@router.get(
    "/qi-card/success",
    summary="Qi Card payment success redirect",
    include_in_schema=False,
)
async def qi_card_success(
    CartID: str = Query(..., description="Our order_id returned by Qi Card"),  # noqa: N803
    db: AsyncSession = Depends(get_db),
):
    """
    Qi Card redirects here on successful payment: successUrl?CartID=<order_id>
    Confirms the escrow in the database then redirects the user to the result page.
    """
    settings = get_settings()
    logger.info("Qi Card success redirect: CartID=%s", CartID)

    service = PaymentService(db)
    success = await service.confirm_qi_card_payment(order_id=CartID)

    if success:
        return RedirectResponse(
            url=f"https://{settings.DOMAIN}/payment/result?status=success&order={CartID}",
            status_code=302,
        )
    # Already processed or not found — still redirect to result page
    return RedirectResponse(
        url=f"https://{settings.DOMAIN}/payment/result?status=success&order={CartID}",
        status_code=302,
    )


@router.get(
    "/qi-card/failure",
    summary="Qi Card payment failure redirect",
    include_in_schema=False,
)
async def qi_card_failure(
    CartID: str = Query("", description="Our order_id returned by Qi Card"),  # noqa: N803
    db: AsyncSession = Depends(get_db),
):
    """Qi Card redirects here on failed payment: failureUrl?CartID=<order_id>"""
    settings = get_settings()
    logger.info("Qi Card failure redirect: CartID=%s", CartID)

    if CartID:
        service = PaymentService(db)
        await service.handle_qi_card_payment_failed(order_id=CartID)

    return RedirectResponse(
        url=f"https://{settings.DOMAIN}/payment/result?status=failed&order={CartID}",
        status_code=302,
    )


@router.get(
    "/qi-card/cancel",
    summary="Qi Card payment cancel redirect",
    include_in_schema=False,
)
async def qi_card_cancel(
    CartID: str = Query("", description="Our order_id returned by Qi Card"),  # noqa: N803
    db: AsyncSession = Depends(get_db),
):
    """Qi Card redirects here on cancelled payment: cancelUrl?CartID=<order_id>"""
    settings = get_settings()
    logger.info("Qi Card cancel redirect: CartID=%s", CartID)

    if CartID:
        service = PaymentService(db)
        await service.handle_qi_card_payment_failed(order_id=CartID)

    return RedirectResponse(
        url=f"https://{settings.DOMAIN}/payment/result?status=cancelled&order={CartID}",
        status_code=302,
    )
