"""
Kaasb Platform - Data Retention Enforcement Task
================================================
Runs as a standalone script (cron job) to enforce data-retention policy.

Policy summary
--------------
| Data type                    | Retention     | Action after TTL    |
|------------------------------|---------------|---------------------|
| Notifications                | 90 days       | Hard-delete         |
| Messages (deleted convos)    | 90 days       | Hard-delete content |
| Deactivated accounts         | 2 years       | Anonymise PII       |
| Revoked refresh tokens       | 30 days       | Hard-delete         |
| Pending reports (no action)  | 6 months      | Auto-dismiss        |
| Audit log                    | 7 years       | Never deleted       |

Run from the project root:
    python -m app.tasks.data_retention

Or via cron (add to /etc/cron.d/kaasb):
    0 3 * * * root cd /app && python -m app.tasks.data_retention >> /var/log/kaasb/data_retention.log 2>&1
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Bootstrap settings (reads DATABASE_URL from environment / .env)
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [data_retention] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def run_retention(db: AsyncSession) -> dict[str, int]:
    """
    Execute all retention policies inside a single transaction.
    Returns a summary dict {policy_name: rows_affected}.
    """
    now = datetime.now(UTC)
    summary: dict[str, int] = {}

    # ------------------------------------------------------------------
    # 1. Archive notifications older than 90 days (soft-delete)
    # ------------------------------------------------------------------
    # Previously hard-deleted. Soft-delete keeps the row available for
    # GDPR export and for dispute post-mortems that surface later. The
    # bell/list queries filter `archived_at IS NULL` so user-facing
    # behaviour is unchanged.
    cutoff_90d = now - timedelta(days=90)
    r = await db.execute(
        sql_text(
            "UPDATE notifications SET archived_at = :now "
            "WHERE created_at < :cutoff AND archived_at IS NULL"
        ),
        {"cutoff": cutoff_90d, "now": now},
    )
    summary["notifications_archived"] = r.rowcount
    logger.info("Notifications archived (>90d): %d", r.rowcount)

    # ------------------------------------------------------------------
    # 2. Delete revoked refresh tokens older than 30 days
    # ------------------------------------------------------------------
    cutoff_30d = now - timedelta(days=30)
    r = await db.execute(
        sql_text(
            "DELETE FROM refresh_tokens "
            "WHERE revoked = true AND updated_at < :cutoff"
        ),
        {"cutoff": cutoff_30d},
    )
    summary["revoked_tokens_deleted"] = r.rowcount
    logger.info("Revoked refresh tokens deleted (>30d): %d", r.rowcount)

    # ------------------------------------------------------------------
    # 3. Anonymise deactivated accounts older than 2 years
    #    (status='deactivated' AND deleted_at IS NULL AND updated_at < 2yr)
    # ------------------------------------------------------------------
    cutoff_2yr = now - timedelta(days=730)
    r = await db.execute(
        sql_text("""
            UPDATE users SET
                email            = CONCAT('anon_', LEFT(id::text, 8), '@deleted.kaasb'),
                username         = CONCAT('anon_', LEFT(id::text, 8)),
                hashed_password  = '',
                first_name       = 'Anonymous',
                last_name        = 'User',
                display_name     = NULL,
                avatar_url       = NULL,
                bio              = NULL,
                phone            = NULL,
                portfolio_url    = NULL,
                deleted_at       = NOW()
            WHERE status = 'deactivated'
              AND deleted_at IS NULL
              AND updated_at < :cutoff
        """),
        {"cutoff": cutoff_2yr},
    )
    summary["accounts_anonymised"] = r.rowcount
    logger.info("Deactivated accounts anonymised (>2yr): %d", r.rowcount)

    # ------------------------------------------------------------------
    # 4. Auto-dismiss pending reports older than 6 months
    # ------------------------------------------------------------------
    cutoff_6m = now - timedelta(days=180)
    r = await db.execute(
        sql_text("""
            UPDATE reports SET
                status     = 'dismissed',
                admin_note = 'Auto-dismissed by data retention policy (6 month TTL)',
                reviewed_at = NOW()
            WHERE status = 'pending'
              AND created_at < :cutoff
        """),
        {"cutoff": cutoff_6m},
    )
    summary["reports_auto_dismissed"] = r.rowcount
    logger.info("Stale pending reports auto-dismissed (>6m): %d", r.rowcount)

    await db.commit()
    return summary


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(  # type: ignore[call-overload]
        engine, class_=AsyncSession, expire_on_commit=False
    )

    logger.info("Data retention job starting — policy enforcement run")
    async with AsyncSessionLocal() as db:
        try:
            summary = await run_retention(db)
            logger.info("Data retention job complete: %s", summary)
        except Exception:
            logger.exception("Data retention job failed — rolling back")
            await db.rollback()
            raise
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
