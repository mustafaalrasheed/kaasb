# Kaasb Platform — RTO / RPO Matrix

**Last updated:** 2026-03-27
**Applies to:** Production stack on Hetzner CPX22

---

## Definitions

| Term | Definition |
|------|-----------|
| **RPO** (Recovery Point Objective) | Maximum acceptable data loss measured in time. If RPO = 4h, we must recover to a state no older than 4 hours before the incident. |
| **RTO** (Recovery Time Objective) | Maximum acceptable downtime from incident start to full service restoration. |
| **Current RPO** | What we can actually achieve today with the existing backup strategy. |
| **Current RTO** | What we can actually achieve today with existing restore procedures. |
| **Target RPO / RTO** | Where we want to be. Gaps drive the roadmap. |

---

## Component-Level Targets

### Database (PostgreSQL)

| Scenario | Current RPO | Target RPO | Current RTO | Target RTO | Gap |
|----------|-------------|------------|-------------|------------|-----|
| Full database loss | ≤ 24 h | ≤ 1 h | 2–4 h | ≤ 1 h | WAL archiving not enabled |
| Table-level corruption | ≤ 24 h | ≤ 1 h | 1–3 h | ≤ 30 min | PITR not enabled |
| Bad migration | ≤ 0 min (pre-deploy backup) | ≤ 0 min | 15–60 min | ≤ 15 min | Automated rollback not wired |
| Accidental row deletion | ≤ 24 h | ≤ 5 min | 2–4 h | ≤ 10 min | Requires PITR or row-level audit |

### User-Uploaded Files (backend_uploads volume)

| Scenario | Current RPO | Target RPO | Current RTO | Target RTO | Gap |
|----------|-------------|------------|-------------|------------|-----|
| Volume deletion | ≤ 24 h | ≤ 24 h | 30–60 min | ≤ 15 min | Acceptable; restore process is manual |
| Single file deleted | ≤ 24 h | ≤ 24 h | 15–30 min | ≤ 5 min | Partial tar extract needs docs |
| Corruption | ≤ 24 h | ≤ 24 h | 30–60 min | ≤ 15 min | None |

### Configuration (.env, nginx, docker-compose, SSL)

| Scenario | Current RPO | Target RPO | Current RTO | Target RTO | Gap |
|----------|-------------|------------|-------------|------------|-----|
| Config file deleted | ≤ 24 h | ≤ 24 h | 15 min | ≤ 5 min | Kept in git (except .env) |
| .env.production lost | ≤ 24 h | N/A (secrets manager) | 30 min | ≤ 10 min | Use 1Password/Vault for secrets |
| SSL certificate lost | ≤ 24 h | N/A (re-issue from LE) | 5–15 min | ≤ 5 min | Can re-issue; not critical |

### Full Server (all components)

| Scenario | Current RPO | Target RPO | Current RTO | Target RTO | Gap |
|----------|-------------|------------|-------------|------------|-----|
| Server hardware failure | ≤ 24 h | ≤ 4 h | 3–5 h | ≤ 2 h | No hot standby; DNS TTL slow |
| Data centre failure | ≤ 24 h | ≤ 4 h | 4–6 h | ≤ 2 h | Single region; multi-region not implemented |
| Security breach (clean rebuild) | ≤ 24 h | ≤ 24 h | 4–8 h | ≤ 4 h | Acceptable for v1 |

---

## Backup Retention vs. RPO

| Backup Tier | Frequency | Retention | Effective RPO |
|-------------|-----------|-----------|---------------|
| Daily DB | 02:00 UTC | 7 days | 24 h |
| Weekly DB | Sunday 02:00 UTC | 4 weeks | 7 days |
| Monthly DB | 1st of month 02:00 UTC | 12 months | 31 days |
| Daily Files | 02:00 UTC | 7 days | 24 h |
| Weekly Files | Sunday 02:00 UTC | 4 weeks | 7 days |
| Monthly Files | 1st of month 02:00 UTC | 12 months | 31 days |
| Daily Configs | 02:00 UTC | 7 days | 24 h |
| WAL archiving | Continuous | 7 days (planned) | Minutes (planned) |

---

## Financial Transaction RPO

Transactions are the most sensitive component. Special considerations:

| Data | RPO | Recovery method |
|------|-----|----------------|
| Completed transactions (DB) | ≤ 24 h | Restore from backup |
| In-flight Stripe payments | N/A | Stripe retains payment records independently |
| In-flight Qi Card payments | N/A | Qi Card gateway retains records independently |
| Escrow balances | ≤ 24 h | DB restore + reconcile with payment gateway |

**Financial reconciliation after restore:**
Always cross-check restored `transactions` and `escrows` tables against Stripe and Qi Card dashboards for the data loss window. Any discrepancy must be manually reconciled before re-opening payment operations.

---

## Roadmap: Closing the Gaps

| Priority | Action | Expected RPO Improvement | Expected RTO Improvement |
|----------|--------|--------------------------|--------------------------|
| P1 | Enable WAL archiving in postgresql.conf | 24 h → minutes | No change |
| P1 | Implement PITR restore procedure | Minutes | 2–4 h → 30–60 min |
| P2 | Set up read replica on Hetzner (streaming replication) | Minutes | 3–5 h → 15 min |
| P2 | Reduce DNS TTL to 300s before any planned work | N/A | 4 h → 10 min |
| P3 | Automate config secrets in HashiCorp Vault or 1Password Secrets Automation | N/A | 30 min → 5 min |
| P3 | Multi-region S3 backup replication | N/A | Same RTO, higher backup durability |
| P4 | Blue/green deployment with pre-warmed standby | N/A | Any RTO → near-zero |

---

## Current Backup Storage Locations

| Backup Type | Primary Location | Off-site (if S3 configured) |
|------------|------------------|-----------------------------|
| Daily DB | `/opt/kaasb/backups/db/` | `s3://kaasb-backups/daily/db/` |
| Weekly DB | `/opt/kaasb/backups/db/` | `s3://kaasb-backups/weekly/db/` |
| Monthly DB | `/opt/kaasb/backups/db/` | `s3://kaasb-backups/monthly/db/` |
| User files | `/opt/kaasb/backups/files/` | `s3://kaasb-backups/daily/files/` |
| Configs | `/opt/kaasb/backups/configs/` | `s3://kaasb-backups/daily/configs/` |

> **Note:** Off-site upload requires `S3_BUCKET` to be set in `.env.production`. Until configured, all backups are local-only — a single disk failure would lose all backups alongside the data.
> **Recommendation:** Configure S3 off-site storage before going live with paying users.
