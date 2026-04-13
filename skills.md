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
    raise NotFoundError("Gig not found")
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
    link_type="gig",                     # "contract"|"job"|"proposal"|"gig"|"message"|None
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
`gig_approved`, `gig_rejected`, `gig_submitted`,
`system_alert`

Frontend bell auto-updates (polls `GET /notifications/unread-count` every 30s). No frontend changes needed.

---

### Gig Lifecycle Recipe

Full flow: `pending_review` → (approve) → `active` | (reject) → `rejected` → (edit+resubmit) → `pending_review`

```python
# ── Service method signatures (gig_service.py) ──────────────────────────
async def approve_gig(self, gig_id: uuid.UUID, admin: User) -> Gig:
    # Validates: status must be pending_review
    # Sets: status=active, reviewed_by_id=admin.id, reviewed_at=now()
    # Fires: GIG_APPROVED notification → freelancer

async def reject_gig(self, gig_id: uuid.UUID, reason: str, admin: User) -> Gig:
    # Validates: status must be pending_review or active (active = takedown)
    # Sets: status=rejected, rejection_reason=reason, reviewed_by_id, reviewed_at
    # Fires: GIG_REJECTED notification → freelancer

async def create_gig(self, freelancer: User, data: GigCreate) -> Gig:
    # Sets status=pending_review
    # Fires: GIG_SUBMITTED notification → all active admins

# ── Endpoint signatures (gigs.py) ───────────────────────────────────────
# POST /gigs/admin/{gig_id}/approve  — pass admin from Depends(get_current_admin)
# POST /gigs/admin/{gig_id}/reject?reason=...  — requires min_length=10
# GET  /gigs/admin/pending           — returns list of pending_review gigs
```

**Gig model audit columns** (added migration `a1b2c3d4e5f6`):
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
        amount_usd=float(order.price_paid),   # converts IQD internally (1 USD ≈ 1310 IQD)
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
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_thing(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/things",
        json={"name": "Test", "amount": 5000},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test"
```

Run: `cd backend && pytest tests/unit/ -v` (fast, no DB)
Run: `cd backend && pytest tests/integration/ -v` (requires DB + Redis)

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
