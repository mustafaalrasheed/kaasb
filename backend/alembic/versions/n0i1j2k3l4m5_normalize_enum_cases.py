"""Normalize all uppercase enum values to lowercase

Revision ID: n0i1j2k3l4m5
Revises: m9h0i1j2k3l4
Create Date: 2026-04-19

Problem:
  The initial migration (25c8a4c398f9) created ALL enum types with UPPERCASE
  values (e.g. 'ACTIVE', 'COMPLETED', 'PROPOSAL_RECEIVED') while Python models
  define lowercase values (e.g. 'active', 'completed', 'proposal_received').
  This causes "invalid input value for enum" PostgreSQL errors on any SQL
  WHERE clause that compares an enum column against a Python-model value.

  Affected endpoints: admin stats, payment summary, pending payouts,
  message send (contact_support), any query filtering by enum status.

Fix:
  Idempotent DO blocks rename each uppercase label to lowercase.
  If the uppercase label is already gone (e.g. paymentprovider was recreated
  in a later migration), the IF EXISTS check silently skips it.
  escrowstatus was already normalized in migration l8g9h0i1j2k3 and is
  therefore excluded from this migration.
"""

from alembic import op

revision = "n0i1j2k3l4m5"
down_revision = "m9h0i1j2k3l4"
branch_labels = None
depends_on = None


def _rename(type_name: str, old: str, new: str) -> None:
    """Idempotent rename of a single enum label."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = '{type_name}' AND e.enumlabel = '{old}'
            ) THEN
                ALTER TYPE {type_name} RENAME VALUE '{old}' TO '{new}';
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    # userrole: CLIENT FREELANCER ADMIN
    for old, new in [
        ("CLIENT", "client"),
        ("FREELANCER", "freelancer"),
        ("ADMIN", "admin"),
    ]:
        _rename("userrole", old, new)

    # userstatus: ACTIVE SUSPENDED DEACTIVATED PENDING_VERIFICATION
    for old, new in [
        ("ACTIVE", "active"),
        ("SUSPENDED", "suspended"),
        ("DEACTIVATED", "deactivated"),
        ("PENDING_VERIFICATION", "pending_verification"),
    ]:
        _rename("userstatus", old, new)

    # jobtype: FIXED HOURLY
    for old, new in [
        ("FIXED", "fixed"),
        ("HOURLY", "hourly"),
    ]:
        _rename("jobtype", old, new)

    # experiencelevel: ENTRY INTERMEDIATE EXPERT
    for old, new in [
        ("ENTRY", "entry"),
        ("INTERMEDIATE", "intermediate"),
        ("EXPERT", "expert"),
    ]:
        _rename("experiencelevel", old, new)

    # jobduration: values match the Python enum .value (numeric prefixes preserved)
    for old, new in [
        ("LESS_THAN_1_WEEK", "less_than_1_week"),
        ("ONE_TO_4_WEEKS", "1_to_4_weeks"),
        ("ONE_TO_3_MONTHS", "1_to_3_months"),
        ("THREE_TO_6_MONTHS", "3_to_6_months"),
        ("MORE_THAN_6_MONTHS", "more_than_6_months"),
    ]:
        _rename("jobduration", old, new)

    # jobstatus: DRAFT OPEN IN_PROGRESS COMPLETED CANCELLED CLOSED
    for old, new in [
        ("DRAFT", "draft"),
        ("OPEN", "open"),
        ("IN_PROGRESS", "in_progress"),
        ("COMPLETED", "completed"),
        ("CANCELLED", "cancelled"),
        ("CLOSED", "closed"),
    ]:
        _rename("jobstatus", old, new)

    # proposalstatus: PENDING SHORTLISTED ACCEPTED REJECTED WITHDRAWN
    for old, new in [
        ("PENDING", "pending"),
        ("SHORTLISTED", "shortlisted"),
        ("ACCEPTED", "accepted"),
        ("REJECTED", "rejected"),
        ("WITHDRAWN", "withdrawn"),
    ]:
        _rename("proposalstatus", old, new)

    # contractstatus: ACTIVE COMPLETED CANCELLED DISPUTED PAUSED
    for old, new in [
        ("ACTIVE", "active"),
        ("COMPLETED", "completed"),
        ("CANCELLED", "cancelled"),
        ("DISPUTED", "disputed"),
        ("PAUSED", "paused"),
    ]:
        _rename("contractstatus", old, new)

    # milestonestatus: PENDING IN_PROGRESS SUBMITTED REVISION_REQUESTED APPROVED PAID
    for old, new in [
        ("PENDING", "pending"),
        ("IN_PROGRESS", "in_progress"),
        ("SUBMITTED", "submitted"),
        ("REVISION_REQUESTED", "revision_requested"),
        ("APPROVED", "approved"),
        ("PAID", "paid"),
    ]:
        _rename("milestonestatus", old, new)

    # transactiontype: ESCROW_FUND ESCROW_RELEASE ESCROW_REFUND PLATFORM_FEE PAYOUT
    for old, new in [
        ("ESCROW_FUND", "escrow_fund"),
        ("ESCROW_RELEASE", "escrow_release"),
        ("ESCROW_REFUND", "escrow_refund"),
        ("PLATFORM_FEE", "platform_fee"),
        ("PAYOUT", "payout"),
    ]:
        _rename("transactiontype", old, new)

    # transactionstatus: PENDING PROCESSING COMPLETED FAILED REFUNDED CANCELLED
    for old, new in [
        ("PENDING", "pending"),
        ("PROCESSING", "processing"),
        ("COMPLETED", "completed"),
        ("FAILED", "failed"),
        ("REFUNDED", "refunded"),
        ("CANCELLED", "cancelled"),
    ]:
        _rename("transactionstatus", old, new)

    # paymentaccountstatus: PENDING VERIFIED SUSPENDED
    for old, new in [
        ("PENDING", "pending"),
        ("VERIFIED", "verified"),
        ("SUSPENDED", "suspended"),
    ]:
        _rename("paymentaccountstatus", old, new)

    # paymentprovider: STRIPE WISE MANUAL (may already be gone if recreated in qi_card_only migration)
    for old, new in [
        ("STRIPE", "stripe"),
        ("WISE", "wise"),
        ("MANUAL", "manual"),
    ]:
        _rename("paymentprovider", old, new)

    # notificationtype: all original uppercase values from initial migration
    # (gig_approved, gig_rejected, gig_submitted, gig_needs_revision,
    #  dispute_opened, dispute_resolved were added as lowercase in later migrations)
    for old, new in [
        ("PROPOSAL_RECEIVED", "proposal_received"),
        ("PROPOSAL_ACCEPTED", "proposal_accepted"),
        ("PROPOSAL_REJECTED", "proposal_rejected"),
        ("PROPOSAL_SHORTLISTED", "proposal_shortlisted"),
        ("CONTRACT_CREATED", "contract_created"),
        ("CONTRACT_COMPLETED", "contract_completed"),
        ("MILESTONE_FUNDED", "milestone_funded"),
        ("MILESTONE_SUBMITTED", "milestone_submitted"),
        ("MILESTONE_APPROVED", "milestone_approved"),
        ("MILESTONE_REVISION", "milestone_revision"),
        ("PAYMENT_RECEIVED", "payment_received"),
        ("PAYOUT_COMPLETED", "payout_completed"),
        ("REVIEW_RECEIVED", "review_received"),
        ("NEW_MESSAGE", "new_message"),
        ("SYSTEM_ALERT", "system_alert"),
    ]:
        _rename("notificationtype", old, new)


def downgrade() -> None:
    # Reverse: lowercase → uppercase (idempotent)
    renames = {
        "userrole": [("client", "CLIENT"), ("freelancer", "FREELANCER"), ("admin", "ADMIN")],
        "userstatus": [
            ("active", "ACTIVE"), ("suspended", "SUSPENDED"),
            ("deactivated", "DEACTIVATED"), ("pending_verification", "PENDING_VERIFICATION"),
        ],
        "jobtype": [("fixed", "FIXED"), ("hourly", "HOURLY")],
        "experiencelevel": [("entry", "ENTRY"), ("intermediate", "INTERMEDIATE"), ("expert", "EXPERT")],
        "jobduration": [
            ("less_than_1_week", "LESS_THAN_1_WEEK"), ("1_to_4_weeks", "ONE_TO_4_WEEKS"),
            ("1_to_3_months", "ONE_TO_3_MONTHS"), ("3_to_6_months", "THREE_TO_6_MONTHS"),
            ("more_than_6_months", "MORE_THAN_6_MONTHS"),
        ],
        "jobstatus": [
            ("draft", "DRAFT"), ("open", "OPEN"), ("in_progress", "IN_PROGRESS"),
            ("completed", "COMPLETED"), ("cancelled", "CANCELLED"), ("closed", "CLOSED"),
        ],
        "proposalstatus": [
            ("pending", "PENDING"), ("shortlisted", "SHORTLISTED"), ("accepted", "ACCEPTED"),
            ("rejected", "REJECTED"), ("withdrawn", "WITHDRAWN"),
        ],
        "contractstatus": [
            ("active", "ACTIVE"), ("completed", "COMPLETED"), ("cancelled", "CANCELLED"),
            ("disputed", "DISPUTED"), ("paused", "PAUSED"),
        ],
        "milestonestatus": [
            ("pending", "PENDING"), ("in_progress", "IN_PROGRESS"), ("submitted", "SUBMITTED"),
            ("revision_requested", "REVISION_REQUESTED"), ("approved", "APPROVED"), ("paid", "PAID"),
        ],
        "transactiontype": [
            ("escrow_fund", "ESCROW_FUND"), ("escrow_release", "ESCROW_RELEASE"),
            ("escrow_refund", "ESCROW_REFUND"), ("platform_fee", "PLATFORM_FEE"), ("payout", "PAYOUT"),
        ],
        "transactionstatus": [
            ("pending", "PENDING"), ("processing", "PROCESSING"), ("completed", "COMPLETED"),
            ("failed", "FAILED"), ("refunded", "REFUNDED"), ("cancelled", "CANCELLED"),
        ],
        "paymentaccountstatus": [
            ("pending", "PENDING"), ("verified", "VERIFIED"), ("suspended", "SUSPENDED"),
        ],
        "notificationtype": [
            ("proposal_received", "PROPOSAL_RECEIVED"), ("proposal_accepted", "PROPOSAL_ACCEPTED"),
            ("proposal_rejected", "PROPOSAL_REJECTED"), ("proposal_shortlisted", "PROPOSAL_SHORTLISTED"),
            ("contract_created", "CONTRACT_CREATED"), ("contract_completed", "CONTRACT_COMPLETED"),
            ("milestone_funded", "MILESTONE_FUNDED"), ("milestone_submitted", "MILESTONE_SUBMITTED"),
            ("milestone_approved", "MILESTONE_APPROVED"), ("milestone_revision", "MILESTONE_REVISION"),
            ("payment_received", "PAYMENT_RECEIVED"), ("payout_completed", "PAYOUT_COMPLETED"),
            ("review_received", "REVIEW_RECEIVED"), ("new_message", "NEW_MESSAGE"),
            ("system_alert", "SYSTEM_ALERT"),
        ],
    }
    for type_name, pairs in renames.items():
        for old, new in pairs:
            _rename(type_name, old, new)
