# 🚀 Kaasb - Freelancing Platform

A modern freelancing marketplace connecting talented freelancers with clients worldwide. Built from scratch with best-in-class technologies.

## Tech Stack

| Layer       | Technology                          |
| ----------- | ----------------------------------- |
| **Backend** | FastAPI + SQLAlchemy 2.0 (async)    |
| **Frontend**| Next.js 15 + TypeScript + Tailwind  |
| **Database**| PostgreSQL 16                       |
| **Cache**   | Redis 7                             |
| **Auth**    | JWT (access + refresh tokens)       |
| **State**   | Zustand                             |

## Project Structure

```
kaasb/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/endpoints/  # Route handlers
│   │   ├── core/              # Config, DB, security
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   └── main.py            # App entry point
│   ├── alembic/               # Database migrations
│   ├── tests/
│   └── requirements.txt
├── frontend/                # Next.js frontend
│   ├── src/
│   │   ├── app/               # Next.js App Router pages
│   │   ├── components/        # Reusable UI components
│   │   ├── lib/               # API client, stores, utils
│   │   ├── types/             # TypeScript type definitions
│   │   └── styles/            # Global CSS
│   └── package.json
├── docker/                  # Dockerfiles
├── docker-compose.yml       # Full stack orchestration
└── README.md
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and navigate to project
cd kaasb

# Start everything
docker compose up -d

# Verify
curl http://localhost:8000/api/v1/health
open http://localhost:3000
```

### Option 2: Manual Setup

**Backend:**
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

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints (Step 1)

| Method | Endpoint              | Description               |
| ------ | --------------------- | ------------------------- |
| GET    | `/`                   | API info                  |
| GET    | `/api/v1/health`      | Health check + DB status  |
| POST   | `/api/v1/auth/register` | Create new account      |
| POST   | `/api/v1/auth/login`  | Login (get JWT tokens)    |
| POST   | `/api/v1/auth/refresh`| Refresh JWT tokens        |
| GET    | `/api/v1/auth/me`     | Current user profile      |

**API Docs:** http://localhost:8000/docs (Swagger UI)

## Development Roadmap

- [x] **Step 1:** Project setup, auth system, landing page
- [ ] **Step 2:** User profiles & profile editing
- [ ] **Step 3:** Job posting & listing
- [ ] **Step 4:** Proposals & bidding system
- [ ] **Step 5:** Contracts & milestones
- [ ] **Step 6:** Messaging system
- [ ] **Step 7:** Payment integration (Stripe + Wise)
- [ ] **Step 8:** Reviews & ratings
- [ ] **Step 9:** Search & filters
- [ ] **Step 10:** Admin dashboard
- [ ] **Step 11:** Notifications
- [ ] **Step 12:** Polish & deployment
