# Kaasb Code Patterns

Copy-paste templates for every common task. Use these instead of reading example files.

---

## Backend Patterns

### Adding a New Endpoint (full recipe)

**Step 1 — Schema** in `backend/app/schemas/<domain>.py`:
```python
from __future__ import annotations
import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ThingCreate(BaseModel):
    name: str
    amount: Decimal

class ThingOut(BaseModel):
    id: uuid.UUID
    name: str
    amount: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

**Step 2 — Service method** in `backend/app/services/<domain>_service.py`:
```python
from app.services.base import BaseService
from app.models.thing import Thing
from app.schemas.thing import ThingCreate, ThingOut
from app.core.exceptions import NotFoundError, ForbiddenError

class ThingService(BaseService):
    async def create_thing(self, user: User, data: ThingCreate) -> Thing:
        thing = Thing(owner_id=user.id, **data.model_dump())
        self.db.add(thing)
        await self.db.commit()
        await self.db.refresh(thing)
        return thing

    async def get_thing(self, thing_id: uuid.UUID, user: User) -> Thing:
        result = await self.db.execute(
            select(Thing).where(Thing.id == thing_id)
        )
        thing = result.scalar_one_or_none()
        if not thing:
            raise NotFoundError("Thing not found")
        if thing.owner_id != user.id:
            raise ForbiddenError("Access denied")
        return thing
```

**Step 3 — Router handler** in `backend/app/api/v1/endpoints/<domain>.py`:
```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user, get_current_admin, get_db
from app.models.user import User
from app.schemas.thing import ThingCreate, ThingOut
from app.services.thing_service import ThingService

router = APIRouter(prefix="/things", tags=["things"])

@router.post("", response_model=ThingOut, status_code=status.HTTP_201_CREATED)
async def create_thing(
    data: ThingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThingOut:
    return await ThingService(db).create_thing(current_user, data)

@router.get("/{thing_id}", response_model=ThingOut)
async def get_thing(
    thing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThingOut:
    return await ThingService(db).get_thing(thing_id, current_user)
```

**Step 4 — Register** in `backend/app/api/v1/router.py`:
```python
from app.api.v1.endpoints.thing import router as thing_router
api_router.include_router(thing_router)
```

**Step 5 — API client** in `frontend/src/lib/api.ts`:
```typescript
export const createThing = (data: ThingCreate): Promise<ThingOut> =>
  api.post<ThingOut>('/things', data).then(r => r.data);

export const getThing = (id: string): Promise<ThingOut> =>
  api.get<ThingOut>(`/things/${id}`).then(r => r.data);
```

---

### Adding a New Database Model + Migration

**Step 1 — Model** in `backend/app/models/<name>.py`:
```python
from __future__ import annotations
import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel

class Thing(BaseModel):
    __tablename__ = "things"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    owner: Mapped["User"] = relationship("User", lazy="raise")
```

**Step 2 — Import** in `backend/app/models/__init__.py`:
```python
from app.models.thing import Thing  # noqa: F401
```

**Step 3 — Generate + apply**:
```bash
cd backend
alembic revision --autogenerate -m "add_things_table"
# Review generated file, then:
alembic upgrade head
alembic check   # must return "No new upgrade operations detected"
```

**Picking a revision ID manually when alembic isn't installed locally** (Windows dev without a venv):

```python
# /c/ProgramData/Anaconda3/python.exe -c "..."
import re, os
revs, downs = {}, set()
d = 'backend/alembic/versions'
for name in sorted(os.listdir(d)):
    if not name.endswith('.py') or name.startswith('__'): continue
    txt = open(os.path.join(d, name), encoding='utf-8').read()
    # Two patterns in this repo: `revision = "..."` AND `revision: str = "..."`
    r = re.search(r'^revision[^=]*=\s*[\"\'](.+?)[\"\']', txt, re.MULTILINE)
    dr = re.search(r'^down_revision[^=]*=\s*[\"\'](.+?)[\"\']', txt, re.MULTILINE)
    if r: revs[name] = r.group(1)
    if dr: downs.add(dr.group(1))
# HEADS = revs that nobody else points at
print('Heads:', [f'{r} <- {f}' for f, r in revs.items() if r not in downs])
```

Chain your new migration behind the single head returned. Do NOT reuse a revision ID that already exists elsewhere in the chain — a simple `revision=` grep catches the `revision = "..."` style but misses `revision: str = "..."`, which is how the 2026-04-25 collision happened.

**Enum pattern** (idempotent — always use this for new enums):
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE thingstatus AS ENUM ('active', 'inactive', 'archived');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.create_table('things',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM(
            'active', 'inactive', 'archived',
            name='thingstatus', create_type=False
        ), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

def downgrade() -> None:
    op.drop_table('things')
    op.execute("DROP TYPE IF EXISTS thingstatus")
```

---

### Error Handling Pattern

```python
from app.core.exceptions import (
    NotFoundError,      # 404 — resource not found
    ForbiddenError,     # 403 — user lacks permission
    UnauthorizedError,  # 401 — not authenticated
    ConflictError,      # 409 — duplicate or state conflict
    BadRequestError,    # 400 — invalid input not caught by Pydantic
    RateLimitError,     # 429 — too many requests
    ExternalServiceError,  # 502 — QiCard/email/external API failed
)

# Standard usage:
if not resource:
    raise NotFoundError("Service not found")
if resource.owner_id != user.id:
    raise ForbiddenError("You do not own this resource")
if await self._already_exists(user.id, job_id):
    raise ConflictError("You already submitted a proposal for this job")
```

Never raise `HTTPException` in services — only in routers (and even then, prefer domain exceptions).

---

### Querying with Relationships (never trigger lazy="raise")

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

# Single related object
stmt = select(Contract).options(
    selectinload(Contract.milestones),
    joinedload(Contract.client),
    joinedload(Contract.freelancer),
).where(Contract.id == contract_id)
result = await self.db.execute(stmt)
contract = result.unique().scalar_one_or_none()

# List with pagination
stmt = (
    select(Job)
    .options(selectinload(Job.proposals))
    .where(Job.status == JobStatus.OPEN)
    .order_by(Job.created_at.desc())
    .offset((page - 1) * page_size)
    .limit(page_size)
)
result = await self.db.execute(stmt)
jobs = result.scalars().all()
```

---

### Notification + Email Pattern

```python
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.models.notification import NotificationType
import asyncio

# In any service method, after the main action:
notif_svc = NotificationService(self.db)
await notif_svc.create(
    user_id=recipient.id,
    notification_type=NotificationType.PAYMENT_RECEIVED,
    title="دفعة جديدة",
    message=f"استلمت دفعة بقيمة {amount} دينار",
    link_type="contract",
    link_id=contract.id,
    actor_id=sender.id,
)

# Email is fire-and-forget — never await in request handler
email_svc = EmailService()
asyncio.create_task(
    email_svc.send_notification_email(
        to_email=recipient.email,
        subject="دفعة جديدة على Kaasb",
        template="payment_received",
        context={"user_name": recipient.first_name, "amount": str(amount)},
    )
)
```

---

### Background Task Pattern

```python
import asyncio
from app.services.email_service import EmailService

@router.post("/my-endpoint")
async def my_endpoint(
    data: MyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MyOut:
    result = await MyService(db).do_thing(current_user, data)
    # Fire-and-forget side effect
    asyncio.create_task(send_side_effect_email(result))
    return result

async def send_side_effect_email(result: MyThing) -> None:
    await EmailService().send_notification_email(...)
```

---

## Frontend Patterns

### Adding a New Page

**SSR page** (public, SEO-important):
```typescript
// frontend/src/app/my-section/page.tsx
import { cookies } from 'next/headers';
import type { Metadata } from 'next';

export async function generateMetadata(): Promise<Metadata> {
  const cookieStore = await cookies();
  const ar = cookieStore.get('locale')?.value !== 'en';
  return {
    title: ar ? 'قسمي | كاسب' : 'My Section | Kaasb',
    description: ar ? 'وصف بالعربية' : 'English description',
  };
}

export default async function MyPage() {
  const cookieStore = await cookies();
  const ar = cookieStore.get('locale')?.value !== 'en';
  // Fetch data server-side if needed
  return (
    <main>
      <h1>{ar ? 'قسمي' : 'My Section'}</h1>
    </main>
  );
}

export const revalidate = 3600; // ISR — omit for pure SSR
```

**CSR dashboard page**:
```typescript
// frontend/src/app/dashboard/my-feature/page.tsx
"use client";
import { useEffect, useState } from 'react';
import { useLocale } from '@/providers/locale-provider';
import { getMyThings } from '@/lib/api';
import type { ThingOut } from '@/types/thing';

export default function MyFeaturePage() {
  const { locale } = useLocale();
  const ar = locale === 'ar';
  const [items, setItems] = useState<ThingOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyThings()
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>{ar ? 'جاري التحميل...' : 'Loading...'}</div>;

  return (
    <div dir={ar ? 'rtl' : 'ltr'}>
      <h1 className="text-2xl font-bold mb-6">
        {ar ? 'خدماتي' : 'My Things'}
      </h1>
      {/* render items */}
    </div>
  );
}
```

---

### API Client Pattern

All calls go in `frontend/src/lib/api.ts`. The axios instance is already configured with interceptors.

```typescript
// Add at the bottom of src/lib/api.ts

// List with pagination
export const listThings = (params?: { page?: number; search?: string }) =>
  api.get<{ items: ThingOut[]; total: number }>('/things', { params }).then(r => r.data);

// Create
export const createThing = (data: ThingCreate) =>
  api.post<ThingOut>('/things', data).then(r => r.data);

// Get by ID
export const getThing = (id: string) =>
  api.get<ThingOut>(`/things/${id}`).then(r => r.data);

// Update
export const updateThing = (id: string, data: Partial<ThingCreate>) =>
  api.put<ThingOut>(`/things/${id}`, data).then(r => r.data);

// Delete
export const deleteThing = (id: string) =>
  api.delete(`/things/${id}`).then(r => r.data);

// Action endpoint
export const activateThing = (id: string) =>
  api.post<ThingOut>(`/things/${id}/activate`).then(r => r.data);
```

---

### Form Handling Pattern (React Hook Form + Zod)

```typescript
"use client";
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useLocale } from '@/providers/locale-provider';
import { createThing } from '@/lib/api';

const schema = z.object({
  name: z.string().min(3).max(200),
  amount: z.number().positive(),
});
type FormData = z.infer<typeof schema>;

export function CreateThingForm() {
  const { locale } = useLocale();
  const ar = locale === 'ar';

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    await createThing(data);
    // handle success
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} dir={ar ? 'rtl' : 'ltr'}>
      <input {...register('name')} placeholder={ar ? 'الاسم' : 'Name'} />
      {errors.name && <p className="text-red-500 text-sm">{errors.name.message}</p>}

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? (ar ? 'جاري الحفظ...' : 'Saving...') : (ar ? 'حفظ' : 'Save')}
      </button>
    </form>
  );
}
```

---

### i18n Pattern

**Client component** — use `useLocale()`:
```typescript
import { useLocale } from '@/providers/locale-provider';

export function MyComponent() {
  const { locale } = useLocale();
  const ar = locale === 'ar';
  return (
    <div dir={ar ? 'rtl' : 'ltr'} className={ar ? 'font-arabic' : ''}>
      <h1>{ar ? 'العنوان' : 'Title'}</h1>
      <p className="text-start">{ar ? 'النص' : 'Text'}</p>
    </div>
  );
}
```

**Server component** — read cookie directly:
```typescript
import { cookies } from 'next/headers';

export default async function MyPage() {
  const cookieStore = await cookies();
  const ar = cookieStore.get('locale')?.value !== 'en';
  return <h1>{ar ? 'مرحباً' : 'Hello'}</h1>;
}
```

**RTL Tailwind** — always use logical properties:
```
ms-4 (not ml-4)   ps-6 (not pl-6)   text-start (not text-left)
me-4 (not mr-4)   pe-6 (not pr-6)   border-s (not border-l)
```

---

### Adding a New Notification Event

```python
# 1. If adding a new notification TYPE, extend the enum in:
#    backend/app/models/notification.py — NotificationType enum
#    Then add a migration using ALTER TYPE ... ADD VALUE IF NOT EXISTS:
#
#    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'your_type'")
#
#    Note: PostgreSQL enum values cannot be removed — downgrade is a no-op.

# 2. In the service where the event occurs, use the convenience function:
import asyncio
from app.services.notification_service import notify
from app.models.notification import NotificationType

# Fire-and-forget (never block the request on notification delivery):
asyncio.create_task(notify(
    self.db,
    user_id=target_user.id,
    type=NotificationType.YOUR_NEW_TYPE,
    title="العنوان",                     # Arabic first
    message="رسالة تفصيلية للمستخدم",
    link_type="service",                 # "contract"|"job"|"proposal"|"service"|"message"|None
    link_id=str(related_entity.id),      # str(UUID) or None
    actor_id=str(triggering_user.id),    # str(UUID) or None
))
```

**Current NotificationType values:**
`proposal_received`, `proposal_accepted`, `proposal_rejected`, `proposal_shortlisted`,
`contract_created`, `contract_completed`,
`milestone_funded`, `milestone_submitted`, `milestone_approved`, `milestone_revision`,
`payment_received`, `payout_completed`,
`review_received`, `new_message`,
`service_approved`, `service_rejected`, `service_submitted`,
`system_alert`

Frontend bell auto-updates (polls `GET /notifications/unread-count` every 30s). No frontend changes needed.

---

### Service Lifecycle Recipe

> Renamed from "Gig" in migration `z2v3w4x5y6z7` (2026-04-21). Old `/gigs` URLs 308-redirect to `/services`; a deprecated `/gigs` alias router on the backend stays for one release.

Full flow: `pending_review` → (approve) → `active` | (reject) → `rejected` → (edit+resubmit) → `pending_review`

```python
# ── Service method signatures (catalog_service.py — class is CatalogService) ─
async def approve_service(self, service_id: uuid.UUID, admin: User) -> Service:
    # Validates: status must be pending_review
    # Sets: status=active, reviewed_by_id=admin.id, reviewed_at=now()
    # Fires: SERVICE_APPROVED notification → freelancer

async def reject_service(self, service_id: uuid.UUID, reason: str, admin: User) -> Service:
    # Validates: status must be pending_review or active (active = takedown)
    # Sets: status=rejected, rejection_reason=reason, reviewed_by_id, reviewed_at
    # Fires: SERVICE_REJECTED notification → freelancer

async def create_service(self, freelancer: User, data: ServiceCreate) -> Service:
    # Sets status=pending_review
    # Fires: SERVICE_SUBMITTED notification → all active admins

# ── Endpoint signatures (services.py) ──────────────────────────────────
# POST /services/admin/{service_id}/approve  — pass admin from Depends(get_current_admin)
# POST /services/admin/{service_id}/reject?reason=...  — requires min_length=10
# GET  /services/admin/pending               — returns list of pending_review services
```

**Service model audit columns** (added migration `a1b2c3d4e5f6`):
- `reviewed_by_id` — UUID FK → users.id (SET NULL on delete)
- `reviewed_at` — TIMESTAMPTZ
- `rejection_reason` — Text (already existed)

**Admin UI** (`src/app/admin/page.tsx`):
- "Make Admin" (blue) — for non-admin users, excluding self
- "Revoke Admin" (orange) — for existing admins, excluding self
- On revoke: backend resets `primary_role → CLIENT` (prevents role label staying as "admin")

---

### QiCard Payment Flow

```python
# Initiate (in a service method):
from app.services.qi_card_client import QiCardClient, QiCardError
from app.core.exceptions import ExternalServiceError

qi = QiCardClient()
try:
    result = await qi.create_payment(
        amount_iqd=int(order.price_paid),     # price is IQD; QiCard accepts whole IQD
        order_id=f"order-{order.id}",
        success_url=f"{settings.FRONTEND_URL}/payment/result?status=success",
        failure_url=f"{settings.FRONTEND_URL}/payment/result?status=failure",
        cancel_url=f"{settings.FRONTEND_URL}/payment/result?status=cancel",
    )
    redirect_url = result["link"]
    amount_iqd = result["amount_iqd"]
except QiCardError as e:
    raise ExternalServiceError(str(e))

# When QI_CARD_API_KEY is not set → returns mock link (dev mode, no error).
```

Frontend `payment/result` page reads `?status=success&CartID=<order_id>`, calls backend to confirm, backend updates order + creates Escrow.

**QiCard API surface (confirmed from v1 3DS OpenAPI, 2026-04-21)** — the gateway exposes **only** 4 endpoints: `POST /payment` (create), `GET /payment/{id}/status`, `POST /payment/{id}/cancel`, `POST /payment/{id}/refund` (full + partial, v1 only). **There is no payout / transfer / disbursement endpoint in any version.** Payouts to freelancers are 100% manual via the QiCard merchant app — the admin matches on `payment_accounts.qi_card_phone` + `qi_card_holder_name` (both required before `release_escrow_by_id` succeeds). Any code that looks for a payout API is wrong; direct it to `admin → Payouts tab → Confirm Payout` instead.

**Escrow after confirmed payment**:
```python
from app.models.payment import Escrow, EscrowStatus
from datetime import datetime, UTC

escrow = Escrow(
    amount=order.price_paid,
    platform_fee=order.price_paid * Decimal("0.10"),
    freelancer_amount=order.price_paid * Decimal("0.90"),
    currency="IQD",
    status=EscrowStatus.FUNDED,
    funded_at=datetime.now(UTC),
    client_id=order.client_id,
    freelancer_id=order.freelancer_id,
)
self.db.add(escrow)
await self.db.commit()
```

---

### Writing Tests

**Unit test** — `backend/tests/unit/test_<feature>.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.thing_service import ThingService
from app.core.exceptions import NotFoundError

@pytest.mark.asyncio
async def test_get_thing_not_found():
    mock_db = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    svc = ThingService(mock_db)
    with pytest.raises(NotFoundError):
        await svc.get_thing(uuid.uuid4(), mock_user)
```

**Integration test** — `backend/tests/integration/test_<feature>.py`:

Service-level integration tests that hit real Postgres. Three non-obvious requirements (from the Phase 5b 4-commit debugging tour, 2026-04-23):

1. **Always mark with `loop_scope="session"`** — conftest's `asyncio_default_fixture_loop_scope = "session"` but tests default to function loop. Without this, asyncpg connections are bound to one loop and awaited on another → `RuntimeError: got Future attached to a different loop`.

2. **Patch `QiCardClient` at the IMPORT site, not the module**. `catalog_service.py` does `qi_card = QiCardClient()` inline; patching `app.services.qi_card_client.QiCardClient` misses it.

3. **`await db_session.refresh(obj)` after any service call that used `synchronize_session=False`** (e.g., `place_order` does a bulk UPDATE on `Service.orders_count` — the in-memory instance stays stale).

Template — reference `backend/tests/integration/test_service_order_placement.py`:

```python
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service, ServiceCategory, ServicePackage, ServicePackageTier, ServiceStatus
from app.models.user import User
from app.schemas.service import ServiceOrderCreate
from app.services.catalog_service import CatalogService


@pytest_asyncio.fixture
async def active_service(db_session: AsyncSession, sample_freelancer_user: User) -> Service:
    cat = ServiceCategory(
        id=uuid.uuid4(), name_en="X", name_ar="X",
        slug=f"x-{uuid.uuid4().hex[:6]}", is_active=True,
    )
    db_session.add(cat)
    await db_session.flush()
    svc = Service(
        id=uuid.uuid4(),
        freelancer_id=sample_freelancer_user.id,
        category_id=cat.id,
        title="...", description="...",
        slug=f"test-{uuid.uuid4().hex[:6]}",
        status=ServiceStatus.ACTIVE,
    )
    db_session.add(svc)
    await db_session.flush()
    return svc


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")   # ← MANDATORY
async def test_something(db_session, sample_client_user, active_service):
    with patch("app.services.catalog_service.QiCardClient") as MockQi:  # ← import site
        MockQi.return_value.create_payment = AsyncMock(return_value={"link": "..."})
        result = await CatalogService(db_session).some_method(...)
    await db_session.refresh(active_service)   # ← if bulk UPDATE happened
    assert active_service.orders_count == 1
```

Run: `cd backend && pytest tests/unit/ -v` (fast, no DB)
Run: `cd backend && pytest tests/integration/ -v` (requires DB + Redis from CI services / docker compose)

---

### Frontend smoke test (Playwright)

Read-only page-load checks against live production. Lives in `frontend/tests/e2e/*.spec.ts`. Runs locally in ~12s; in CI on every push to main.

```typescript
import { expect, test } from "@playwright/test";

test.describe("My page smoke", () => {
    test("returns 200 and has expected content", async ({ page }) => {
        const response = await page.goto("/my-page");
        expect(response?.status()).toBe(200);

        // BODY-level text search — avoid `locator('main')` because
        // layout.tsx wraps children in its own <main>, strict mode
        // rejects ambiguous selectors.
        await expect(page.locator("body")).toContainText("expected copy");
    });
});
```

Non-obvious rules (from 2026-04-24 CI debugging):

- **Use `body` selectors for text, not `main`** — nested `<main>` elements (layout's + page's) trip strict mode.
- **JSON-LD tolerance** — pages can have multiple `ld+json` script tags (Organization, Website, FAQPage). Scan all with `allTextContents()` and match on `"@type":"FaqPage"` pattern, don't assume there's only one.
- **Don't assert on a page behaviour that your current commit hasn't deployed yet** — Playwright runs against live `kaasb.com`, so a new-footer-link assertion fails on the very push that introduces the footer link. Add the assertion in a follow-up commit after the deploy lands.

Run locally: `cd frontend && npm run test:smoke` (12s)  
Run with UI: `cd frontend && npm run test:smoke:ui` (step through each test visually)

---

### Regenerating frontend lockfile (when package.json changed)

When adding or bumping a frontend dep without Node locally (or when it's easier to let CI do it):

```bash
gh workflow run regenerate-lockfile.yml --ref main
# Wait ~90s
gh run list --workflow=regenerate-lockfile.yml --limit 1
# If the workflow pushed a branch but couldn't open its own PR (Actions
# isn't allowed to create PRs by default — the repo setting is at
# Settings → Actions → General → "Allow GitHub Actions to create and
# approve pull requests"; once flipped, future runs open PRs themselves):
gh pr create --title "chore(deps): regenerate frontend/package-lock.json" \
  --body "Auto-regenerated" --base main \
  --head "$(git ls-remote --heads origin 'chore/regenerate-lockfile-*' | tail -1 | sed 's|.*refs/heads/||')"
gh pr merge <number> --squash --delete-branch --admin
```

---

### Watching CI + retrying failed jobs

```bash
# Latest run on main
gh run list --workflow=ci.yml --branch=main --limit 1

# Watch until done
gh run watch <id> --exit-status --interval 10

# Show per-job status
gh run view <id> --json conclusion,jobs -q '{c: .conclusion, j: [.jobs[] | {n: .name, c: .conclusion}]}'

# Retry ONLY the failed jobs (don't re-spend compute on green ones — common
# after transient GHCR 502s on "Build & Push Docker Images")
gh run rerun <id> --failed

# Tail failed logs (greps for the actionable lines)
gh run view <id> --log-failed 2>&1 | grep -E "FAILED|ERROR|AssertionError|TypeError|ImportError" | head -40
```

---

## Domain Exception Reference

| Exception | HTTP | Raise when |
|-----------|------|-----------|
| `NotFoundError` | 404 | Resource doesn't exist |
| `ForbiddenError` | 403 | User doesn't own / lacks role |
| `UnauthorizedError` | 401 | Not logged in |
| `ConflictError` | 409 | Duplicate key or invalid state transition |
| `BadRequestError` | 400 | Business rule violation not caught by Pydantic |
| `RateLimitError` | 429 | Exceeded per-IP/user limit |
| `ExternalServiceError` | 502 | QiCard / email / SMS call failed |

---

## Rate Limits (configured in `backend/app/middleware/security.py`)

| Endpoint group | Limit |
|----------------|-------|
| Login | 5 req / 5 min |
| Register | 3 req / 10 min |
| Standard API | 120 req / min |
| Payment | 10 req / min |
| OTP | 3 req / hour per phone/email |

---

## Auth Dependencies Reference

```python
from app.api.dependencies import (
    get_current_user,          # any authenticated user
    get_current_admin,         # must have primary_role == admin
    get_current_freelancer,    # must have primary_role == freelancer
    get_current_client,        # must have primary_role == client
    get_db,                    # AsyncSession
)
```

Social login: `POST /auth/social` with `{"provider": "google"|"facebook", "token": "<access_token>"}`.
Backend calls provider's userinfo endpoint. Looks up by `google_id`/`facebook_id` first, email second.
