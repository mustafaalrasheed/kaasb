# Kaasb Platform — Skills Reference
Token-efficient pattern guide. Read this instead of re-reading the whole codebase.

---

## How to Add a New API Endpoint

**Step 1 — Add schema** in `backend/app/schemas/<domain>.py`:
```python
class MyThingCreate(BaseModel):
    name: str
    amount: Decimal

class MyThingOut(BaseModel):
    id: uuid.UUID
    name: str
    amount: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

**Step 2 — Add service method** in `backend/app/services/<domain>_service.py`:
```python
async def create_thing(self, user: User, data: MyThingCreate) -> MyThing:
    thing = MyThing(owner_id=user.id, **data.model_dump())
    self.db.add(thing)
    await self.db.commit()
    await self.db.refresh(thing)
    return thing
```
- Raise `NotFoundError`, `ForbiddenError`, `ConflictError`, `BadRequestError` from `app.core.exceptions`.
- Use `selectinload()` on relationships (never `lazy="raise"` at query time).
- All DB operations are `async` — `await` every SQLAlchemy call.

**Step 3 — Add router handler** in `backend/app/api/v1/endpoints/<domain>.py`:
```python
@router.post("", response_model=MyThingOut, status_code=status.HTTP_201_CREATED)
async def create_thing(
    data: MyThingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = MyThingService(db)
    return await svc.create_thing(current_user, data)
```
- Import your service. No SQL logic here.
- Use `Depends(get_current_admin)` for admin-only routes.
- Use `Depends(get_current_freelancer)` or `Depends(get_current_client)` when role matters.

**Step 4 — Register router** in `backend/app/api/v1/router.py`:
```python
from app.api.v1.endpoints.my_thing import router as my_thing_router
api_router.include_router(my_thing_router, prefix="/my-things")
```

**Step 5 — Add API call** in `frontend/src/lib/api.ts`:
```typescript
export const createThing = (data: MyThingCreate) =>
  api.post<MyThingOut>('/my-things', data).then(r => r.data);
```

---

## How to Add a New Database Model + Migration

**Step 1 — Create model** in `backend/app/models/<name>.py`:
```python
from app.models.base import BaseModel
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

class MyThing(BaseModel):
    __tablename__ = "my_things"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
```

**Step 2 — Import model** in `backend/app/models/base.py` or wherever models are loaded:
Ensure it's imported before `alembic` autogenerate runs.

**Step 3 — Generate migration**:
```bash
cd backend
alembic revision --autogenerate -m "add_my_things_table"
# Review the generated file in alembic/versions/
alembic upgrade head
alembic check   # must show "No new upgrade operations detected"
```

**Enum type pattern** (idempotent):
```python
def upgrade():
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mythingstatus AS ENUM ('active', 'inactive');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.create_table('my_things',
        sa.Column('status', postgresql.ENUM('active', 'inactive',
            name='mythingstatus', create_type=False), nullable=False),
        ...
    )
```

---

## How to Add a New Frontend Page

**Step 1 — Create page file**:
```
frontend/src/app/my-section/page.tsx         # /my-section
frontend/src/app/my-section/[id]/page.tsx    # /my-section/[id]
```

**Step 2 — Choose rendering strategy**:
- Public/SEO pages: use `async` server component (SSR)
- Dashboard/user-specific: use `"use client"` + CSR
- Semi-static catalog: add `export const revalidate = 3600` for ISR

**Step 3 — SSR page pattern**:
```typescript
// app/my-section/page.tsx — server component
export default async function MyPage() {
  const data = await fetchData();  // direct fetch or server-side API call
  return <MyComponent data={data} />;
}
export const metadata = { title: 'My Page | Kaasb', description: '...' };
```

**Step 4 — CSR page pattern**:
```typescript
"use client";
import { useEffect, useState } from 'react';
import { fetchMyThings } from '@/lib/api';

export default function MyDashboardPage() {
  const [data, setData] = useState([]);
  useEffect(() => { fetchMyThings().then(setData); }, []);
  return <div>{/* render */}</div>;
}
```

**Step 5 — Protect dashboard pages**: Already handled by `src/middleware.ts`.
Any path under `/dashboard/` is auto-protected. No per-page auth check needed.

---

## How to Add Translations (Arabic + English)

**i18n approach**: Cookie-based locale (`ar` default, `en` secondary). No `next-intl` — locale
is read server-side via `cookies()` and exposed to client components via `LocaleProvider` context.

**Client components** — use the `useLocale()` hook:
```typescript
import { useLocale } from '@/providers/locale-provider';

export function MyComponent() {
  const { locale } = useLocale();
  const ar = locale === 'ar';
  return <button>{ar ? 'إنشاء خدمة جديدة' : 'Create New Gig'}</button>;
}
```

**Server components** — read the cookie directly:
```typescript
import { cookies } from 'next/headers';

export default async function MyPage() {
  const cookieStore = await cookies();
  const locale = cookieStore.get('locale')?.value === 'en' ? 'en' : 'ar';
  const ar = locale === 'ar';
  return <h1>{ar ? 'مرحباً' : 'Hello'}</h1>;
}
```

**Bilingual metadata** — use `generateMetadata()` instead of `export const metadata`:
```typescript
export async function generateMetadata() {
  const cookieStore = await cookies();
  const locale = cookieStore.get('locale')?.value === 'en' ? 'en' : 'ar';
  const ar = locale === 'ar';
  return { title: ar ? 'العنوان بالعربية' : 'English Title' };
}
```

**RTL layout**: Arabic is RTL. Use Tailwind logical properties:
- Use `start`/`end` instead of `left`/`right`: `ms-4` not `ml-4`, `ps-6` not `pl-6`
- Use `text-start` not `text-left`
- Use `border-s` not `border-l`
- `dir="rtl"` is set at root layout level — components inherit it automatically.

**Arabic font**: Tajawal is primary. Applied via `font-arabic` class in Tailwind config.

**Translation files**: `frontend/src/messages/ar.json` and `en.json` exist as a reference
dictionary but are not imported at runtime. All translations are inline ternaries.

---

## How to Add a New Notification Event

**Step 1 — Add notification in service** where the event happens:
```python
from app.services.notification_service import NotificationService
from app.models.notification import NotificationType

# Inside your service method, after the main action:
notif_svc = NotificationService(self.db)
await notif_svc.create(
    user_id=freelancer.id,
    notification_type=NotificationType.PAYMENT_RECEIVED,
    title="طلب جديد",
    message=f"لديك طلب جديد على خدمتك: {gig.title}",
    link_type="contract",        # optional: "contract"/"job"/"proposal"/"message"
    link_id=order.id,            # optional: UUID of linked entity
    actor_id=client.id,          # optional: who triggered it
)
```

**Step 2 — Frontend bell updates automatically**: `NotificationBell` component polls
`GET /api/v1/notifications/unread-count` every 30 seconds. New notifications appear immediately.

**Step 3 — Email notification** (if needed): Use `EmailService` in a background task:
```python
import asyncio
email_svc = EmailService()
asyncio.create_task(
    email_svc.send_notification_email(
        to_email=user.email,
        subject="طلب جديد على Kaasb",
        template="order_placed",
        context={"user_name": user.first_name, "order_id": str(order.id)},
    )
)
```
Never `await` email sends in request handlers — always fire-and-forget.

---

## How to Add a QiCard Payment Flow

QiCard is the ONLY payment provider. All payments are in IQD (Iraqi Dinar).
1 USD ≈ 1,310 IQD. `usd_to_iqd()` helper in `qi_card_client.py` converts.

**QiCard flow is redirect-based (no real-time webhook):**
```
POST /api/v0/transactions/business/token → get redirect link
→ redirect user to link → user pays on QiCard portal
→ QiCard redirects to successUrl?CartID=<orderId> (or failureUrl/cancelUrl)
→ your handler at successUrl confirms in DB
```

**Step 1 — Initiate payment**:
```python
from app.services.qi_card_client import QiCardClient, QiCardError

qi = QiCardClient()
try:
    result = await qi.create_payment(
        amount_usd=float(order.price_paid),  # converts to IQD internally
        order_id=f"order-{order.id}",
        success_url=f"{settings.FRONTEND_URL}/payment/result?status=success",
        failure_url=f"{settings.FRONTEND_URL}/payment/result?status=failure",
        cancel_url=f"{settings.FRONTEND_URL}/payment/result?status=cancel",
    )
    # result["link"] = redirect user here
    # result["amount_iqd"] = actual IQD amount charged
except QiCardError as e:
    raise ExternalServiceError(str(e))
```
When `QI_CARD_API_KEY` is not set, the client returns a mock link automatically (dev mode).

**Step 2 — Handle callback** at `/payment/result` (frontend page):
- Read `?status=success&CartID=<order_id>` query params
- Call backend to confirm: `POST /api/v1/payments/qi-card/confirm` with `order_id`
- Backend updates order status, creates Escrow record, notifies freelancer

**Step 3 — Escrow record** (after confirmed payment):
```python
escrow = Escrow(
    amount=order.price_paid,
    platform_fee=order.price_paid * 0.10,
    freelancer_amount=order.price_paid * 0.90,
    currency="IQD",
    status=EscrowStatus.FUNDED,
    funded_at=datetime.now(UTC),
    ...
)
```

**Payout flow (manual — QiCard has no payout API):**
Admin sees funded+completed orders in payout queue.
Admin pays freelancer via QiCard merchant dashboard, then clicks "Mark Paid" in Kaasb admin.
This sets `escrow.status = EscrowStatus.RELEASED` and creates a `PAYOUT` transaction record.

**Refunds**: QiCard v0 API has no refund endpoint. All refunds are manual via merchant portal.
`qi.refund_payment()` always raises `QiCardError` — use it to detect and trigger admin manual flow.

---

## How to Write a Test

**Unit test** (no DB, no Redis) in `tests/unit/`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_something():
    mock_db = AsyncMock()
    service = MyService(mock_db)
    result = await service.do_something(...)
    assert result.name == "expected"
```

**Integration test** (real DB) in `tests/integration/`:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_endpoint(client: AsyncClient, auth_headers: dict):
    response = await client.post("/api/v1/my-things", json={...}, headers=auth_headers)
    assert response.status_code == 201
```
Integration tests use fixtures in `tests/conftest.py` — see existing tests for patterns.

---

## Domain Exception Reference

Raise these from services. `main.py` maps them to HTTP codes automatically.

| Exception | HTTP | When to use |
|-----------|------|-------------|
| `NotFoundError` | 404 | Resource not found |
| `ForbiddenError` | 403 | User lacks permission |
| `UnauthorizedError` | 401 | Not authenticated |
| `ConflictError` | 409 | Duplicate / state conflict |
| `BadRequestError` | 400 | Invalid input not caught by Pydantic |
| `RateLimitError` | 429 | Too many requests |
| `ExternalServiceError` | 502 | QiCard/email/external API failed |

```python
from app.core.exceptions import NotFoundError, ForbiddenError

if not gig:
    raise NotFoundError("Gig not found")
if gig.freelancer_id != current_user.id:
    raise ForbiddenError("You do not own this gig")
```

---

## Rate Limits (configured in `middleware/security.py`)
- Login: 5 req / 5 min
- Register: 3 req / 10 min
- Standard API: 120 req / min
- Payment: 10 req / min
- OTP: 3 req / hour per phone/email
