# Kaasb API — Developer Guide

## Base URLs

| Environment | URL |
|-------------|-----|
| Production | `https://kaasb.com/api/v1` |
| Local Dev | `http://localhost:8000/api/v1` |

## Quick Start (5 minutes)

### Step 1 — Register and get a token

```bash
curl -X POST https://kaasb.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dev@example.com",
    "username": "dev_user",
    "password": "DevPass1!",
    "first_name": "Dev",
    "last_name": "User",
    "primary_role": "client"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Step 2 — Call an authenticated endpoint

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl https://kaasb.com/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Step 3 — Post a job (client role)

```bash
curl -X POST https://kaasb.com/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Build a REST API",
    "description": "Need a FastAPI backend with PostgreSQL...",
    "category": "web_development",
    "job_type": "fixed",
    "budget_min": 500,
    "budget_max": 1500,
    "skills_required": ["Python", "FastAPI"],
    "experience_level": "mid",
    "duration_weeks": 4
  }'
```

---

## Python Integration

### Install dependencies
```bash
pip install httpx
```

### Client class
```python
import httpx
from datetime import datetime, timedelta

class KaasbClient:
    def __init__(self, base_url="https://kaasb.com/api/v1"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self._client = httpx.Client(base_url=base_url, timeout=30)

    def register(self, email, username, password, first_name, last_name, role="freelancer"):
        resp = self._client.post("/auth/register", json={
            "email": email, "username": username, "password": password,
            "first_name": first_name, "last_name": last_name, "primary_role": role
        })
        resp.raise_for_status()
        self._save_tokens(resp.json())
        return resp.json()

    def login(self, email, password):
        resp = self._client.post("/auth/login", json={"email": email, "password": password})
        resp.raise_for_status()
        self._save_tokens(resp.json())
        return resp.json()

    def refresh(self):
        resp = self._client.post("/auth/refresh", json={"refresh_token": self.refresh_token})
        resp.raise_for_status()
        self._save_tokens(resp.json())

    def _save_tokens(self, data):
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self._client.headers["Authorization"] = f"Bearer {self.access_token}"

    def get(self, path, **kwargs):
        resp = self._client.get(path, **kwargs)
        if resp.status_code == 401:
            self.refresh()
            resp = self._client.get(path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def post(self, path, **kwargs):
        resp = self._client.post(path, **kwargs)
        if resp.status_code == 401:
            self.refresh()
            resp = self._client.post(path, **kwargs)
        resp.raise_for_status()
        return resp.json()

# Usage
client = KaasbClient()
client.login("ali@example.com", "Pass1!abc")

# Get current user
me = client.get("/auth/me")
print(f"Logged in as: {me['data']['username']}")

# Search jobs
jobs = client.get("/jobs", params={"q": "python", "job_type": "fixed"})
print(f"Found {jobs['total']} jobs")

# Submit proposal
proposal = client.post(f"/proposals/jobs/{jobs['items'][0]['id']}", json={
    "cover_letter": "I can build this excellently...",
    "bid_amount": 1000,
    "estimated_duration": "3 weeks"
})
```

---

## JavaScript / TypeScript Integration

```typescript
const BASE_URL = "https://kaasb.com/api/v1";

class KaasbClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  private async request(method: string, path: string, body?: unknown) {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.accessToken) headers["Authorization"] = `Bearer ${this.accessToken}`;

    let resp = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    // Auto-refresh on 401
    if (resp.status === 401 && this.refreshToken) {
      await this.refresh();
      headers["Authorization"] = `Bearer ${this.accessToken}`;
      resp = await fetch(`${BASE_URL}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
    }

    if (!resp.ok) throw new Error(`${resp.status}: ${await resp.text()}`);
    return resp.json();
  }

  async login(email: string, password: string) {
    const data = await this.request("POST", "/auth/login", { email, password });
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    return data;
  }

  async refresh() {
    const data = await this.request("POST", "/auth/refresh", { refresh_token: this.refreshToken });
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
  }

  async searchJobs(params: Record<string, string>) {
    const qs = new URLSearchParams(params).toString();
    return this.request("GET", `/jobs?${qs}`);
  }

  async submitProposal(jobId: string, proposal: unknown) {
    return this.request("POST", `/proposals/jobs/${jobId}`, proposal);
  }
}

// Usage
const client = new KaasbClient();
await client.login("ali@example.com", "Pass1!abc");

const jobs = await client.searchJobs({ q: "python", job_type: "fixed" });
console.log(`Found ${jobs.total} jobs`);
```

---

## Pagination

All list endpoints use cursor-based pagination:

```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

```python
# Fetch all items across pages
def fetch_all(client, path, params=None):
    params = params or {}
    page = 1
    all_items = []
    while True:
        params["page"] = page
        data = client.get(path, params=params)
        all_items.extend(data["items"])
        if page >= data["total_pages"]:
            break
        page += 1
    return all_items
```

---

## WebSocket (Real-time Notifications)

```javascript
// Connect to WebSocket for real-time updates
const ws = new WebSocket(`wss://kaasb.com/api/v1/ws?token=${accessToken}`);

ws.onopen = () => {
  console.log("Connected to Kaasb WebSocket");
  // Send heartbeat every 30 seconds
  setInterval(() => ws.send(JSON.stringify({ type: "ping" })), 30000);
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  switch (msg.type) {
    case "notification":
      console.log("New notification:", msg.data);
      break;
    case "message":
      console.log("New message:", msg.data);
      break;
    case "proposal_accepted":
      console.log("Proposal accepted!", msg.data);
      break;
    case "pong":
      // Heartbeat response
      break;
  }
};

ws.onclose = (event) => {
  console.log("Disconnected:", event.code);
  // Reconnect after 5 seconds
  setTimeout(() => connectWebSocket(), 5000);
};
```

**WebSocket event types:**

| Event | Direction | Description |
|-------|-----------|-------------|
| `ping` | Client → Server | Heartbeat (keep connection alive) |
| `pong` | Server → Client | Heartbeat response |
| `notification` | Server → Client | New notification (proposal, message, etc.) |
| `message` | Server → Client | New chat message |
| `proposal_accepted` | Server → Client | Your proposal was accepted |
| `milestone_submitted` | Server → Client | Freelancer submitted a milestone |
| `milestone_approved` | Server → Client | Client approved your milestone |

> **Note:** WebSocket state is per-Gunicorn worker. In multi-worker deployments, events only reach clients on the same worker. Redis pub/sub support planned for v1.1.

---

## File Uploads (Avatar)

```python
import httpx

with open("avatar.jpg", "rb") as f:
    resp = httpx.post(
        "https://kaasb.com/api/v1/users/avatar",
        headers={"Authorization": f"Bearer {access_token}"},
        files={"file": ("avatar.jpg", f, "image/jpeg")}
    )
resp.raise_for_status()
print("Avatar URL:", resp.json()["data"]["avatar_url"])
```

**Constraints:**
- Formats: JPEG, PNG, WebP
- Max size: 10 MB
- Rate limit: 10 requests/minute

---

## Local Development Setup

```bash
# 1. Clone and start dependencies
git clone https://github.com/mustafaalrasheed/kaasb.git
cd kaasb
docker compose up -d db redis

# 2. Backend setup
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your local values
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Access Swagger docs (DEBUG=True required)
open http://localhost:8000/docs

# 4. Run tests
pytest tests/unit/ -v
```

---

## API Versioning Policy

- Current version: **v1** (URL prefix `/api/v1/`)
- Breaking changes will increment the version to `/api/v2/`
- Old versions supported for **6 months** after new version release
- Non-breaking additions (new fields, new endpoints) do not increment version
- Deprecation notices sent via API response headers: `X-Deprecated: true`, `X-Sunset-Date: 2026-12-01`

---

## Response Envelope

Most endpoints wrap their response in a `data` field:

```json
{ "data": { ... } }
```

List endpoints use:
```json
{
  "items": [...],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

Error responses:
```json
{
  "detail": "Human readable message",
  "code": "KAASB_AUTH_001"
}
```
