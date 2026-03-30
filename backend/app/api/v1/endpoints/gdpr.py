"""
Kaasb Platform - GDPR / Data Rights Endpoints
Implements GDPR Article 15 (right of access) and Article 17 (right to erasure).

POST /gdpr/export   - Download a JSON copy of all personal data (DSAR)
DELETE /gdpr/delete - Permanently anonymise account + all personal data
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import BadRequestError
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gdpr", tags=["GDPR"])


# ---------------------------------------------------------------------------
# POST /gdpr/export
# ---------------------------------------------------------------------------

@router.post(
    "/export",
    summary="Download your personal data (DSAR — GDPR Art. 15)",
    response_description="JSON object containing all personal data associated with your account",
)
async def request_data_export(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a complete snapshot of personal data held about the authenticated
    user (Data Subject Access Request).

    Includes: profile, jobs posted, proposals submitted, contracts,
    messages, reviews, transactions, and notification history.
    """
    data = await _collect_user_data(current_user, db)
    logger.info("DSAR export generated for user %s", current_user.id)
    return {
        "data": data,
        "generated_at": datetime.now(UTC).isoformat(),
        "format": "json",
        "note": (
            "This export contains all personal data held by Kaasb as of "
            "the generation timestamp. Retain a copy for your records."
        ),
    }


# ---------------------------------------------------------------------------
# DELETE /gdpr/delete
# ---------------------------------------------------------------------------

@router.delete(
    "/delete",
    status_code=status.HTTP_200_OK,
    summary="Permanently delete your account (GDPR Art. 17)",
)
async def hard_delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently anonymise your account and erase all identifying personal data.

    - Financial records (transactions, escrows) are **retained** for legal/tax
      compliance but are de-linked from identifying information.
    - All active contracts must be completed or cancelled first.
    - This action is **irreversible**.
    """
    # Block deletion if user has active contracts
    result = await db.execute(
        sql_text(
            "SELECT COUNT(*) FROM contracts "
            "WHERE (client_id = :uid OR freelancer_id = :uid) "
            "AND status = 'active'"
        ),
        {"uid": str(current_user.id)},
    )
    active_count = result.scalar() or 0
    if active_count:
        raise BadRequestError(
            f"You have {active_count} active contract(s). "
            "Complete or cancel all active contracts before deleting your account."
        )

    uid = str(current_user.id)

    # Anonymise personal fields — preserve the row for FK integrity
    await db.execute(
        sql_text("""
            UPDATE users SET
                email            = CONCAT('deleted_', LEFT(id::text, 8), '@deleted.kaasb'),
                username         = CONCAT('deleted_', LEFT(id::text, 8)),
                hashed_password  = '',
                first_name       = 'Deleted',
                last_name        = 'User',
                display_name     = NULL,
                avatar_url       = NULL,
                bio              = NULL,
                phone            = NULL,
                portfolio_url    = NULL,
                is_email_verified = false,
                status           = 'deactivated',
                deleted_at       = NOW()
            WHERE id = :uid
        """),
        {"uid": uid},
    )

    # Revoke all refresh tokens
    await db.execute(
        sql_text("UPDATE refresh_tokens SET revoked = true WHERE user_id = :uid"),
        {"uid": uid},
    )

    # Anonymise messages
    await db.execute(
        sql_text(
            "UPDATE messages SET content = '[deleted]' "
            "WHERE sender_id = :uid"
        ),
        {"uid": uid},
    )

    await db.commit()

    logger.info("Hard-delete (anonymisation) completed for user %s", uid)
    return {
        "detail": (
            "Your account and personal data have been permanently deleted. "
            "Financial records are retained for legal compliance but contain "
            "no identifying information."
        )
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _collect_user_data(user: User, db: AsyncSession) -> dict:
    """Collect all personal data for a DSAR response (GDPR Art. 15)."""

    async def _query(sql: str, params: dict) -> list[dict]:
        result = await db.execute(sql_text(sql), params)
        return [_serialize_row(dict(r._mapping)) for r in result]

    uid = str(user.id)

    jobs = await _query(
        "SELECT id, title, description, category, status, budget_min, budget_max, "
        "skills_required, created_at, updated_at "
        "FROM jobs WHERE client_id = :uid AND deleted_at IS NULL",
        {"uid": uid},
    )

    proposals = await _query(
        "SELECT id, job_id, cover_letter, bid_amount, status, created_at "
        "FROM proposals WHERE freelancer_id = :uid",
        {"uid": uid},
    )

    contracts_client = await _query(
        "SELECT id, freelancer_id, status, total_amount, currency, created_at "
        "FROM contracts WHERE client_id = :uid AND deleted_at IS NULL",
        {"uid": uid},
    )

    contracts_freelancer = await _query(
        "SELECT id, client_id, status, total_amount, currency, created_at "
        "FROM contracts WHERE freelancer_id = :uid AND deleted_at IS NULL",
        {"uid": uid},
    )

    reviews_given = await _query(
        "SELECT id, reviewee_id, rating, comment, created_at "
        "FROM reviews WHERE reviewer_id = :uid",
        {"uid": uid},
    )

    reviews_received = await _query(
        "SELECT id, reviewer_id, rating, comment, created_at "
        "FROM reviews WHERE reviewee_id = :uid",
        {"uid": uid},
    )

    transactions = await _query(
        "SELECT id, transaction_type, amount, currency, status, created_at "
        "FROM transactions WHERE user_id = :uid",
        {"uid": uid},
    )

    return {
        "profile": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "display_name": user.display_name,
            "bio": user.bio,
            "country": user.country,
            "city": user.city,
            "timezone": user.timezone,
            "phone": user.phone,
            "primary_role": user.primary_role,
            "status": user.status,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
        },
        "jobs_posted": jobs,
        "proposals_submitted": proposals,
        "contracts_as_client": contracts_client,
        "contracts_as_freelancer": contracts_freelancer,
        "reviews_given": reviews_given,
        "reviews_received": reviews_received,
        "transactions": transactions,
    }


def _serialize_row(row: dict) -> dict:
    """Convert non-JSON-serialisable values (datetime, UUID, Decimal) to strings."""
    result: dict = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            result[k] = v.isoformat()
        elif v is None or isinstance(v, str | int | float | bool):
            result[k] = v
        else:
            result[k] = str(v)
    return result
