# Kaasb - Freelancing Platform

A modern freelancing marketplace connecting talented freelancers with clients worldwide. Built from scratch with best-in-class technologies.

## Tech Stack

| Layer        | Technology                         |
| ------------ | ---------------------------------- |
| **Backend**  | FastAPI + SQLAlchemy 2.0 (async)   |
| **Frontend** | Next.js 15 + TypeScript + Tailwind |
| **Database** | PostgreSQL 16                      |
| **Cache**    | Redis 7                            |
| **Auth**     | JWT (access + refresh tokens)      |
| **State**    | Zustand                            |

## Project Structure

```
kaasb/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/endpoints/  # Route handlers
│   │   ├── core/              # Config, DB, security, rate limiter
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── utils/             # File upload utilities
│   │   └── main.py            # App entry point
│   ├── alembic/               # Database migrations
│   ├── .env.example           # Environment variable template
│   └── requirements.txt
├── frontend/                # Next.js frontend
│   ├── src/
│   │   ├── app/               # Next.js App Router pages
│   │   ├── components/        # Reusable UI components
│   │   ├── lib/               # API client, stores, utils
│   │   ├── types/             # TypeScript type definitions
│   │   └── styles/            # Global CSS
│   └── package.json
├── docker-compose.yml       # Full stack orchestration
├── .env.example             # Root environment template
└── README.md
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and navigate to project
git clone https://github.com/YOUR_USERNAME/kaasb.git
cd kaasb

# Copy environment files and fill in your values
cp .env.example .env
cp backend/.env.example backend/.env

# Start everything
docker compose up -d

# Verify
curl http://localhost:8000/api/v1/health
```

### Option 2: Manual Setup

**1. Environment**
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your database credentials and a strong SECRET_KEY
# Generate one with: openssl rand -hex 32
```

**2. Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL and Redis (or use Docker for just the DBs)
docker compose up -d db redis

# Run the backend
uvicorn app.main:app --reload --port 8000
```

**3. Frontend**
```bash
cd frontend
npm install
npm run dev
```

## Running Tests

```bash
# Start the backend first, then from the project root:
python test_api.py
```

## API Reference

| Method | Endpoint                            | Auth       | Description                     |
| ------ | ----------------------------------- | ---------- | ------------------------------- |
| GET    | `/api/v1/health`                    | Public     | Health check + DB status        |
| POST   | `/api/v1/auth/register`             | Public     | Create account (5 req/min)      |
| POST   | `/api/v1/auth/login`                | Public     | Login — returns JWT (10 req/min)|
| POST   | `/api/v1/auth/refresh`              | Public     | Refresh JWT tokens              |
| GET    | `/api/v1/auth/me`                   | Required   | Current user profile            |
| GET    | `/api/v1/users/profile/{username}`  | Public     | Public user profile             |
| PUT    | `/api/v1/users/profile`             | Required   | Update own profile              |
| GET    | `/api/v1/jobs`                      | Public     | Browse & search open jobs       |
| POST   | `/api/v1/jobs`                      | Client     | Create job posting              |
| GET    | `/api/v1/jobs/{job_id}`             | Public     | Job details                     |
| POST   | `/api/v1/proposals/jobs/{job_id}`   | Freelancer | Submit proposal                 |
| GET    | `/api/v1/proposals/my`              | Freelancer | My proposals                    |
| POST   | `/api/v1/proposals/{id}/respond`    | Client     | Accept / shortlist / reject     |

**API Docs:** http://localhost:8000/docs (Swagger UI, development only)

## Security

- Secrets are **never committed** — copy `.env.example` to `.env` and fill in your own values.
- Generate a strong JWT secret: `openssl rand -hex 32`
- Auth endpoints are rate-limited per IP (register: 5/min, login: 10/min).
- All responses include security headers (X-Content-Type-Options, X-Frame-Options, etc.).
- File uploads are validated against actual file bytes via `python-magic` (not just the Content-Type header).

## Development Roadmap

- [x] **Step 1:** Project setup, auth system, landing page
- [x] **Step 2:** User profiles & profile editing
- [x] **Step 3:** Job posting & listing
- [x] **Step 4:** Proposals & bidding system
- [ ] **Step 5:** Contracts & milestones
- [ ] **Step 6:** Messaging system
- [ ] **Step 7:** Payment integration (Stripe + Wise)
- [ ] **Step 8:** Reviews & ratings
- [ ] **Step 9:** Search & filters
- [ ] **Step 10:** Admin dashboard
- [ ] **Step 11:** Notifications
- [ ] **Step 12:** Polish & deployment
