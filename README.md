# Kaasb — Freelancing Marketplace Platform

A full-stack freelancing marketplace connecting clients with freelancers globally, with special support for Iraqi freelancers through alternative payment solutions.

## Tech Stack

**Backend:** FastAPI · SQLAlchemy 2.0 · PostgreSQL · Redis · Alembic
**Frontend:** Next.js 16 · TypeScript · Tailwind CSS
**Payments:** Stripe (global) · Wise API (Iraq/MENA)
**DevOps:** Docker · Nginx · GitHub Actions CI/CD

## Features

| Feature | Description |
|---------|-------------|
| **Authentication** | JWT + refresh tokens, role-based access (client/freelancer/admin) |
| **User Profiles** | Skills, portfolio, avatar, hourly rate, experience level |
| **Job Posting** | CRUD with search, filters, categories, budget ranges |
| **Proposals** | Submit, shortlist, accept/reject with cover letters |
| **Contracts** | Milestone-based with status tracking |
| **Payments** | Stripe + Wise hybrid, 10% platform fee, escrow system |
| **Reviews** | 1-5 star ratings with category scores, aggregated stats |
| **Messaging** | Real-time conversations with unread tracking |
| **Notifications** | 15 event types, mark-read, badge counts |
| **Admin Dashboard** | Platform stats, user management, job moderation, transactions |
| **Security** | Rate limiting, security headers, input sanitization |

## Quick Start (Development)

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+

### Option 1: Docker (recommended)

```bash
docker compose up -d
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Option 2: Manual

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Edit with your values
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Create Admin User

```bash
cd backend
python -m scripts.create_admin
```

### Run Tests

```bash
# Start backend first, then:
python test_api.py
# Expected: 26/26 passed
```

## Production Deployment

### 1. Configure

```bash
cp .env.production.template .env.production
# Edit with real values: DB_PASSWORD, SECRET_KEY, STRIPE keys, DOMAIN
```

### 2. Deploy

```bash
chmod +x deploy.sh
./deploy.sh           # Full deployment
```

### 3. Manage

```bash
./deploy.sh --status        # Service status
./deploy.sh --logs          # View logs
./deploy.sh --logs backend  # Backend only
./deploy.sh --migrate       # Run migrations
./deploy.sh --create-admin  # Create admin user
./deploy.sh --restart       # Restart services
./deploy.sh --stop          # Stop all
```

## Architecture

```
kaasb/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # Route handlers (11 route files)
│   │   ├── core/              # Config, database, security
│   │   ├── middleware/         # Rate limiting, security headers
│   │   ├── models/            # SQLAlchemy models (9 model files)
│   │   ├── schemas/           # Pydantic validation (8 schema files)
│   │   ├── services/          # Business logic (9 service files)
│   │   └── utils/             # Sanitization helpers
│   ├── alembic/               # Database migrations
│   └── scripts/               # Admin utilities
├── frontend/
│   └── src/
│       ├── app/               # Next.js pages (10 page dirs)
│       ├── lib/               # API client, auth store
│       └── types/             # TypeScript types (8 type files)
├── docker/
│   ├── backend/Dockerfile     # Multi-stage build
│   ├── frontend/Dockerfile    # Multi-stage build
│   └── nginx/nginx.conf       # Reverse proxy
├── .github/workflows/ci.yml   # CI/CD pipeline
├── docker-compose.yml         # Development
├── docker-compose.prod.yml    # Production
└── deploy.sh                  # Deployment script
```

## API Endpoints (30 total)

| Group | Endpoints | Auth |
|-------|-----------|------|
| Health | `GET /health` | Public |
| Auth | `POST /register`, `/login`, `/refresh` | Public |
| Users | `GET/PUT /me`, `GET /users/{id}` | Auth |
| Jobs | CRUD + search + filters | Mixed |
| Proposals | Submit, list, respond | Auth |
| Contracts | Create, milestones, lifecycle | Auth |
| Payments | Escrow, payout, accounts, summary | Auth |
| Reviews | Submit, list, stats | Mixed |
| Notifications | List, mark-read, unread-count | Auth |
| Messages | Conversations, send, read | Auth |
| Admin | Stats, users, jobs, transactions | Admin |

Full interactive docs: `http://localhost:8000/docs`

## Payment Flow

1. **Client funds escrow** → Stripe charges card → money held
2. **Freelancer works** → submits milestone deliverables
3. **Client approves** → escrow released, 10% platform fee deducted
4. **Freelancer requests payout** → sent via Wise (Iraq) or Stripe (global)

## License

MIT
