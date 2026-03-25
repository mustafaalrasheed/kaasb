# Contributing to Kaasb

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.production.example ../.env
# Edit .env with your database credentials
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Code Style

### Python (Backend)
- **Linter**: Ruff (`ruff check .` / `ruff format .`)
- **Type hints**: Required on all function signatures and return types
- **Docstrings**: Required on all public functions and classes
- **Logging**: Use lazy `%s` formatting, never f-strings in logger calls
- **Imports**: Group as stdlib → third-party → local, sorted by `isort`
- **Services**: Inherit from `BaseService`, use `self.paginated_response()`
- **Exceptions**: Raise domain exceptions (`NotFoundError`, etc.), not `HTTPException` in services

### TypeScript (Frontend)
- **Linter**: ESLint with Next.js rules
- **Types**: No `any` — use proper interfaces from `@/types/`
- **Components**: Extract reusable UI into `@/components/ui/`
- **Constants**: Centralize magic values in `@/lib/constants.ts`
- **State**: Use Zustand stores for global state
- **API calls**: Use typed API functions from `@/lib/api.ts`

## Git Conventions

### Branch Naming
- `feature/description` — New features
- `fix/description` — Bug fixes
- `refactor/description` — Code improvements
- `docs/description` — Documentation changes

### Commit Messages
Follow conventional commits:
```
type: short description

Longer explanation if needed.
```

Types: `feat`, `fix`, `refactor`, `perf`, `security`, `docs`, `test`, `ci`

### Pull Requests
- Keep PRs focused — one feature/fix per PR
- Include tests for new business logic
- Update documentation if API changes
- All CI checks must pass

## Architecture

### Backend (FastAPI)
```
backend/app/
├── api/          # Route handlers (thin — delegate to services)
├── core/         # Config, database, security, exceptions
├── middleware/    # Rate limiting, security headers, CSRF
├── models/       # SQLAlchemy ORM models
├── schemas/      # Pydantic request/response models
├── services/     # Business logic (inherit BaseService)
└── utils/        # Shared utilities (sanitize, files)
```

### Frontend (Next.js)
```
frontend/src/
├── app/          # Pages (App Router)
├── components/   # Reusable UI components
├── lib/          # API client, auth store, utilities
└── types/        # TypeScript interfaces
```

## Testing

### Running Tests
```bash
cd backend
pytest                          # All tests
pytest tests/unit/              # Unit tests only
pytest -v --tb=short            # Verbose with short tracebacks
pytest --cov=app --cov-report=term  # With coverage
```

### Writing Tests
- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use fixtures from `tests/conftest.py`
- Name test files `test_*.py` and test functions `test_*`
