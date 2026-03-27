# Kaasb Platform — Business Continuity Plan (BCP)

**Last updated:** 2026-03-27
**Version:** 1.0
**Owner:** Platform Engineering / Business Owner

---

## 1. Purpose and Scope

This Business Continuity Plan (BCP) defines how Kaasb responds to service disruptions, data incidents, and operational crises to minimise impact on users, freelancers, clients, and the business.

**In scope:** Production platform (kaasb.com), database, payment processing, user data.
**Out of scope:** Internal tooling, staging environment, development workflows.

---

## 2. Incident Severity Classification

| Level | Definition | Examples | Response Time |
|-------|-----------|----------|---------------|
| **P0 — Critical** | Complete service outage or data loss/breach | Server down, DB corrupt, security breach | Immediate (< 15 min) |
| **P1 — High** | Core feature unavailable or degraded | Payments failing, login broken, migrations failing | < 1 hour |
| **P2 — Medium** | Non-critical feature degraded | Slow queries, background jobs failing, minor UI issues | < 4 hours |
| **P3 — Low** | Cosmetic or minor issues | Styling bug, non-critical API slowness | Next business day |

---

## 3. Communication Plan

### 3.1 Internal Escalation Path

```
Automated Monitor Alert
        ↓
  On-Call Engineer (first responder)
        ↓  (if P0/P1 not resolved in 30 min)
  Platform Lead
        ↓  (if P0 and financial impact)
  Business Owner
        ↓  (if data breach / legal requirement)
  Legal Counsel / DPO
```

### 3.2 Contact List

> Store contacts in team password manager, not in this document.

| Role | Responsibility | Contact Key |
|------|---------------|-------------|
| On-Call Engineer | First responder, triage | `contacts/oncall-engineer` |
| Platform Lead | Escalation, architecture decisions | `contacts/platform-lead` |
| Business Owner | User communication, legal decisions | `contacts/business-owner` |
| Hetzner Support | Hardware / network failures | console.hetzner.cloud → Support |
| Stripe Support | Payment processing issues | dashboard.stripe.com → Support |
| Domain Registrar | DNS emergencies | Fastcomet/Hetzner DNS console |

### 3.3 Status Page

During incidents, update the status page (or create a simple notice at kaasb.com):

```bash
# Quick maintenance notice via nginx
# Edit docker/nginx/nginx.conf to return 503 with maintenance page for all routes except /health
docker compose -f /opt/kaasb/docker-compose.prod.yml --env-file /opt/kaasb/.env.production \
    restart nginx
```

---

## 4. User Communication Templates

### 4.1 Service Outage (Social Media / Email)

```
Subject: Kaasb is temporarily unavailable

We are currently experiencing a technical issue affecting [SERVICE].
Our team is working to resolve it as quickly as possible.

Expected resolution: [TIME or "We will update within X hours"]
Current status: [Investigating / Identified / Fixing / Monitoring]

We apologise for the inconvenience.
— The Kaasb Team
```

**Arabic:**
```
نعتذر عن التوقف المؤقت في خدمة [SERVICE].
يعمل فريقنا على حل المشكلة في أقرب وقت ممكن.
الوقت المتوقع للإصلاح: [TIME]
— فريق كسب
```

### 4.2 Data Incident Notification (GDPR Art. 34)

> Use only if personal data was accessed by unauthorised parties.
> Consult legal counsel before sending.

```
Subject: Important security notice from Kaasb

Dear [User Name],

We are writing to inform you of a security incident that may have affected
your account on Kaasb.

What happened:
[Brief description — e.g., "On [DATE], we discovered unauthorised access to our systems."]

What information was involved:
[e.g., email addresses, hashed passwords, profile information]

What we are doing:
- We have secured our systems and changed all access credentials.
- We have notified the relevant data protection authority.
- We are enhancing our security measures.

What you should do:
- Change your Kaasb password immediately.
- If you used the same password elsewhere, change it there too.
- Be alert for phishing emails pretending to be from Kaasb.

Contact us: support@kaasb.com

We sincerely apologise for this incident.
— The Kaasb Team
```

### 4.3 Regulatory Notification (GDPR Art. 33)

Within 72 hours of becoming aware of a personal data breach, notify the competent supervisory authority.

Required information:
- Nature of the breach (what happened, how many records)
- Categories of data (names, emails, financial data, etc.)
- Approximate number of individuals affected
- Name and contact of the Data Protection Officer
- Likely consequences of the breach
- Measures taken or proposed to address the breach

---

## 5. Escalation Decision Tree

```
Incident detected
      │
      ├─ Is kaasb.com reachable? NO ──────────────────────────────────► Scenario 1 or 6
      │
      ├─ Are API responses correct? NO ────────────────────────────────► Check backend logs
      │       └─ DB connection error? ─────────────────────────────────► Scenario 2
      │       └─ Migration error? ───────────────────────────────────── ► Scenario 4
      │
      ├─ Are uploaded files missing? YES ──────────────────────────────► Scenario 3
      │
      ├─ Are there signs of intrusion? YES ────────────────────────────► Scenario 5
      │       (unknown processes, changed files, auth log anomalies)
      │
      └─ Is disk usage > 90%? YES ─────────────────────────────────────► Scenario 6
```

---

## 6. Financial Operations During Outage

### During a P0 outage:

1. **Stripe:** No action needed. Stripe processes and holds payments independently. New payments will fail at checkout (users will see an error); existing successful payments are safe.

2. **Qi Card:** Same as Stripe — gateway operates independently.

3. **Active contracts:** Freelancers with active milestones are not affected unless the outage extends beyond 24 hours. Communicate estimated resolution time.

4. **Escrow funds:** Held in the database. If DB is restored from backup, reconcile escrow balances against payment gateway records before re-enabling payouts.

### After recovery:

```bash
# Verify escrow integrity after restore
docker compose exec db psql -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT
    e.id,
    e.amount,
    e.status,
    e.contract_id,
    t.stripe_payment_intent_id,
    t.qi_card_transaction_id
FROM escrows e
JOIN transactions t ON t.escrow_id = e.id
WHERE e.status = 'held'
ORDER BY e.created_at DESC;
"
```

---

## 7. Disaster Recovery Drill Schedule

Regular drills ensure the recovery procedures work before they are needed in a real emergency.

### Monthly Drill (automated)

Runs on the 1st of each month at 04:00 UTC:
```bash
# /etc/cron.d/kaasb
0 4 1 * * root bash /opt/kaasb/scripts/backup-verify.sh >> /var/log/kaasb/backup-verify.log 2>&1
```

The drill verifies:
- Backup file integrity (gzip + SHA-256)
- Live restore to a temporary container
- Row counts in key tables

### Quarterly Drill (manual — full restore test)

**Schedule:** First Monday of each quarter.

```bash
# 1. Provision a temporary Hetzner server (CX11 is sufficient for testing)
# 2. Run the full restore scenario from Scenario 1
# 3. Verify all services start and health endpoints pass
# 4. Record results in the drill log below
# 5. Terminate the temporary server
```

### Drill Log

| Date | Drill Type | Result | RTO Achieved | Notes |
|------|-----------|--------|--------------|-------|
| 2026-04-01 | Monthly automated | Pending | — | First scheduled run |
| 2026-04-07 | Quarterly full restore | Pending | — | First quarterly drill |

---

## 8. Key Operational Contacts and Accounts

> All credentials are stored in the team password manager, not in this document.

| Service | Purpose | Access Key |
|---------|---------|-----------|
| Hetzner Cloud | Server and volume management | `accounts/hetzner` |
| GitHub | Source code, Actions secrets | `accounts/github` |
| Stripe Dashboard | Payment management, refunds | `accounts/stripe` |
| Qi Card Gateway | IQD payment management | `accounts/qi-card` |
| Wise Dashboard | Payout management | `accounts/wise` |
| Cloudflare / DNS | DNS management | `accounts/dns` |
| Domain Registrar | Domain renewals | `accounts/registrar` |
| Sentry | Error monitoring | `accounts/sentry` |

---

## 9. BCP Review and Maintenance

This document must be reviewed and updated:
- After every P0 or P1 incident
- After every quarterly DR drill
- When infrastructure changes significantly
- At minimum, every 6 months

**Next scheduled review:** 2026-09-27
