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
from app.services.zain_cash_client import ZainCashClient, ZainCashError

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
    """Set up a Qi Card payment account."""
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
    sig: str = Query("", description="HMAC-SHA256 signature of order_id"),
    db: AsyncSession = Depends(get_db),
):
    """
    Qi Card redirects here on successful payment: successUrl?sig=<hmac>&CartID=<order_id>
    The sig is verified before confirming the payment — prevents users from faking
    payment by hitting this URL directly with a known order_id.
    """
    settings = get_settings()
    logger.info("Qi Card success redirect: CartID=%s", CartID)

    service = PaymentService(db)
    success = await service.confirm_qi_card_payment(order_id=CartID, sig=sig)

    if success:
        return RedirectResponse(
            url=f"https://{settings.DOMAIN}/payment/result?status=success&order={CartID}",
            status_code=302,
        )
    # Signature invalid, payment not found, or already processed
    return RedirectResponse(
        url=f"https://{settings.DOMAIN}/payment/result?status=error&order={CartID}",
        status_code=302,
    )


@router.get(
    "/qi-card/failure",
    summary="Qi Card payment failure redirect",
    include_in_schema=False,
)
async def qi_card_failure(
    CartID: str = Query("", description="Our order_id returned by Qi Card"),  # noqa: N803
    sig: str = Query("", description="HMAC-SHA256 signature of order_id"),
    db: AsyncSession = Depends(get_db),
):
    """Qi Card redirects here on failed payment: failureUrl?sig=<hmac>&CartID=<order_id>"""
    settings = get_settings()
    logger.info("Qi Card failure redirect: CartID=%s", CartID)

    if CartID:
        service = PaymentService(db)
        await service.handle_qi_card_payment_failed(order_id=CartID, sig=sig)

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
    sig: str = Query("", description="HMAC-SHA256 signature of order_id"),
    db: AsyncSession = Depends(get_db),
):
    """Qi Card redirects here on cancelled payment: cancelUrl?sig=<hmac>&CartID=<order_id>"""
    settings = get_settings()
    logger.info("Qi Card cancel redirect: CartID=%s", CartID)

    if CartID:
        service = PaymentService(db)
        await service.handle_qi_card_payment_failed(order_id=CartID, sig=sig)

    return RedirectResponse(
        url=f"https://{settings.DOMAIN}/payment/result?status=cancelled&order={CartID}",
        status_code=302,
    )


# === Zain Cash callbacks ============================================
#
# Zain Cash uses a single redirect URL (not three like Qi Card) — the buyer
# always lands here regardless of success / failure / cancel. The actual
# outcome lives in a JWT appended as ?token=<jwt>, signed with our merchant
# secret. Defense in depth:
#   * verify the JWT — proves Zain Cash sent it (only ZC + Kaasb know the
#     merchant secret), and gives us a tamper-proof orderId + status.
#   * verify our own sig — proves the URL was issued by us in fund_escrow,
#     so an attacker forging a JWT with their own ZC merchant account can't
#     replay it against an orderId we never created.

@router.get(
    "/zain-cash/callback",
    summary="Zain Cash payment callback (single URL, JWT-signed)",
    include_in_schema=False,
)
async def zain_cash_callback(
    token: str = Query(..., description="JWT signed by our merchant secret"),
    sig: str = Query("", description="HMAC-SHA256 signature of order_id"),
    db: AsyncSession = Depends(get_db),
):
    """Zain Cash appends ?token=<jwt> to our redirectUrl after the buyer
    pays / fails / cancels. The JWT carries ``orderId`` + ``status``
    (\"success\" or anything else)."""
    settings = get_settings()
    zc = ZainCashClient()
    try:
        claims = zc.verify_redirect_token(token)
    except ZainCashError as exc:
        logger.warning("zain_cash callback token rejected: %s", exc)
        return RedirectResponse(
            url=f"https://{settings.DOMAIN}/payment/result?status=error",
            status_code=302,
        )

    order_id = str(claims.get("orderId", ""))
    status = str(claims.get("status", "")).lower()
    logger.info(
        "zain_cash callback: order=%s status=%s op=%s",
        order_id, status, claims.get("operationId"),
    )

    if not order_id:
        return RedirectResponse(
            url=f"https://{settings.DOMAIN}/payment/result?status=error",
            status_code=302,
        )

    service = PaymentService(db)
    if status == "success":
        # confirm_qi_card_payment is gateway-agnostic at the persistence
        # layer — it looks up the escrow by order_id, marks it FUNDED,
        # marks the funding Transaction COMPLETED. Reusing it for
        # Zain Cash means a single code path drives both gateways.
        # TODO(rename): drop the qi_card prefix from these methods in a
        # future refactor — they don't actually care which gateway sent
        # the callback once the entry-point JWT/sig is verified.
        ok = await service.confirm_qi_card_payment(order_id=order_id, sig=sig)
        result_status = "success" if ok else "error"
    else:
        await service.handle_qi_card_payment_failed(order_id=order_id, sig=sig)
        result_status = "failed" if status in {"failed", "failure"} else "cancelled"

    return RedirectResponse(
        url=f"https://{settings.DOMAIN}/payment/result?status={result_status}&order={order_id}",
        status_code=302,
    )
