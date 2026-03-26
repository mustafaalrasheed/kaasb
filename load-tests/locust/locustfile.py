"""
Kaasb Platform — Locust Load Test Suite
========================================
Simulates realistic Iraqi freelancing platform traffic patterns.

Usage:
  # Web UI (recommended for first runs):
  locust -f locustfile.py --host=https://kaasb.com

  # Headless / CI mode:
  locust -f locustfile.py --host=https://kaasb.com \
    --users=100 --spawn-rate=10 --run-time=10m --headless \
    --csv=reports/results

  # Specific user class only:
  locust -f locustfile.py --host=https://kaasb.com \
    --users=50 --spawn-rate=5 --run-time=5m --headless \
    BrowseUser

Iraqi peak hours: 19:00–23:00 Baghdad time (UTC+3)
Weekend: Thursday evening + Friday (higher traffic)

Install:
  pip install locust faker
"""

import json
import random
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from locust import HttpUser, TaskSet, task, between, events
from locust.exception import StopUser

from data.generator import IraqiDataGenerator, gen

# ── Shared state (jobs/proposals created by test users) ───────────────────────
_shared = {
    "open_job_ids":      [],   # populated by ClientUser
    "proposal_ids":      [],   # populated by FreelancerUser
    "contract_ids":      [],   # populated by ContractUser
    "public_usernames":  [],   # populated on register
    "conversation_ids":  [],   # populated by ChatUser
}

# ── Base class with auth helpers ───────────────────────────────────────────────

class KaasbUser(HttpUser):
    """Base class — provides login/register helpers and request logging."""

    abstract = True
    wait_time = between(1, 4)  # Think time between tasks (seconds)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gen   = IraqiDataGenerator()
        self.token  = None
        self.user_id = None
        self.role   = None
        self._user_data = None

    # ── Auth helpers ────────────────────────────────────────────────────────

    def register_and_login(self, role: str) -> bool:
        """Register a new user and store the JWT token."""
        self._user_data = self._gen.user(role=role)
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email":        self._user_data["email"],
                "username":     self._user_data["username"],
                "password":     self._user_data["password"],
                "first_name":   self._user_data["first_name"],
                "last_name":    self._user_data["last_name"],
                "primary_role": role,
            },
            name="/api/v1/auth/register",
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            self.token   = data.get("access_token")
            self.role    = role
            # Extract user_id from JWT payload (middle part)
            try:
                import base64
                payload_b64 = self.token.split(".")[1]
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64))
                self.user_id = payload.get("sub")
            except Exception:
                pass
            # Track public username for browse tests
            if self._user_data.get("username"):
                _shared["public_usernames"].append(self._user_data["username"])
            return True
        return False

    def login(self, email: str, password: str) -> bool:
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="/api/v1/auth/login",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")
            return True
        return False

    @property
    def auth_headers(self) -> dict:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def get_auth(self, url: str, **kwargs) -> object:
        return self.client.get(url, headers=self.auth_headers, **kwargs)

    def post_auth(self, url: str, **kwargs) -> object:
        return self.client.post(url, headers=self.auth_headers, **kwargs)

    def put_auth(self, url: str, **kwargs) -> object:
        return self.client.put(url, headers=self.auth_headers, **kwargs)

    def delete_auth(self, url: str, **kwargs) -> object:
        return self.client.delete(url, headers=self.auth_headers, **kwargs)


# ══════════════════════════════════════════════════════════════════════════════
# 1. BROWSE USER — searches without account (60% of traffic)
# ══════════════════════════════════════════════════════════════════════════════

class BrowseUser(KaasbUser):
    """
    Anonymous / browsing user — the majority of Kaasb traffic.
    Does NOT log in. Represents users exploring the platform.
    Weight: 60% of total virtual users.
    """

    weight    = 60
    wait_time = between(2, 6)

    def on_start(self):
        pass  # No login needed

    @task(5)
    def browse_jobs(self):
        params = self._gen.job_search_query()
        self.client.get(
            "/api/v1/jobs",
            params=params,
            name="/api/v1/jobs [search]",
        )

    @task(3)
    def view_job_detail(self):
        if not _shared["open_job_ids"]:
            self.browse_jobs()
            return
        job_id = random.choice(_shared["open_job_ids"])
        self.client.get(
            f"/api/v1/jobs/{job_id}",
            name="/api/v1/jobs/:id [detail]",
        )

    @task(3)
    def browse_freelancers(self):
        params = self._gen.freelancer_search_query()
        self.client.get(
            "/api/v1/users/freelancers",
            params=params,
            name="/api/v1/users/freelancers [search]",
        )

    @task(2)
    def view_freelancer_profile(self):
        if not _shared["public_usernames"]:
            return
        username = random.choice(_shared["public_usernames"])
        self.client.get(
            f"/api/v1/users/profile/{username}",
            name="/api/v1/users/profile/:username",
        )

    @task(1)
    def check_health(self):
        self.client.get("/api/v1/health", name="/api/v1/health")

    @task(1)
    def browse_deep_pagination(self):
        """Tests deep pagination queries — can be slow."""
        self.client.get(
            "/api/v1/jobs",
            params={"page": random.randint(50, 200), "page_size": 20},
            name="/api/v1/jobs [deep page]",
        )


# ══════════════════════════════════════════════════════════════════════════════
# 2. AUTH USER — heavy auth operations (login storms, token refresh)
# ══════════════════════════════════════════════════════════════════════════════

class AuthUser(KaasbUser):
    """
    Tests authentication endpoints under load.
    Simulates: register, login, token refresh, profile view, logout.
    Weight: 10% of traffic.
    """

    weight    = 10
    wait_time = between(1, 3)

    def on_start(self):
        role = random.choice(["client", "freelancer"])
        if not self.register_and_login(role):
            raise StopUser()

    @task(2)
    def view_my_profile(self):
        self.get_auth("/api/v1/auth/me", name="/api/v1/auth/me")

    @task(1)
    def refresh_token(self):
        """Simulate token refresh (clients with long sessions)."""
        resp = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": ""},  # Uses httpOnly cookie fallback
            name="/api/v1/auth/refresh",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", self.token)

    @task(3)
    def update_profile(self):
        if not self.token:
            return
        self.put_auth(
            "/api/v1/users/profile",
            json={
                "bio":   f"Updated bio {random.randint(1000, 9999)}",
                "city":  random.choice(["Baghdad", "Basra", "Erbil"]),
                "country": "Iraq",
            },
            name="/api/v1/users/profile [update]",
        )

    @task(1)
    def check_notifications(self):
        self.get_auth(
            "/api/v1/notifications",
            params={"page": 1, "page_size": 20},
            name="/api/v1/notifications",
        )

    @task(1)
    def get_unread_count(self):
        self.get_auth(
            "/api/v1/notifications/unread-count",
            name="/api/v1/notifications/unread-count",
        )

    def on_stop(self):
        if self.token:
            self.post_auth("/api/v1/auth/logout", json={}, name="/api/v1/auth/logout")


# ══════════════════════════════════════════════════════════════════════════════
# 3. CLIENT USER — posts jobs, reviews proposals, manages contracts
# ══════════════════════════════════════════════════════════════════════════════

class ClientUser(KaasbUser):
    """
    Client flow: register → post jobs → review proposals → accept → manage contract.
    Weight: 10% of traffic.
    """

    weight    = 10
    wait_time = between(2, 5)

    def on_start(self):
        if not self.register_and_login("client"):
            raise StopUser()
        self._my_job_ids       = []
        self._my_proposal_ids  = []  # proposals on MY jobs
        self._my_contract_ids  = []
        self._my_milestone_ids = []

    @task(3)
    def post_job(self):
        job_data = self._gen.job()
        resp = self.post_auth(
            "/api/v1/jobs",
            json=job_data,
            name="/api/v1/jobs [create]",
        )
        if resp.status_code == 201:
            job_id = resp.json().get("id")
            if job_id:
                self._my_job_ids.append(job_id)
                _shared["open_job_ids"].append(job_id)

    @task(2)
    def view_my_posted_jobs(self):
        self.get_auth(
            "/api/v1/jobs/my/posted",
            params={"page": 1, "page_size": 20},
            name="/api/v1/jobs/my/posted",
        )

    @task(2)
    def view_proposals_on_my_job(self):
        if not self._my_job_ids:
            return
        job_id = random.choice(self._my_job_ids)
        resp = self.get_auth(
            f"/api/v1/proposals/jobs/{job_id}/list",
            params={"page": 1, "page_size": 20},
            name="/api/v1/proposals/jobs/:id/list",
        )
        if resp.status_code == 200:
            proposals = resp.json().get("items", [])
            for p in proposals:
                if p.get("id") not in self._my_proposal_ids:
                    self._my_proposal_ids.append(p["id"])

    @task(1)
    def shortlist_proposal(self):
        if not self._my_proposal_ids:
            return
        proposal_id = random.choice(self._my_proposal_ids)
        self.post_auth(
            f"/api/v1/proposals/{proposal_id}/respond",
            json={"action": "shortlist"},
            name="/api/v1/proposals/:id/respond [shortlist]",
        )

    @task(2)
    def view_my_contracts(self):
        resp = self.get_auth(
            "/api/v1/contracts/my",
            params={"page": 1, "page_size": 20},
            name="/api/v1/contracts/my",
        )
        if resp.status_code == 200:
            contracts = resp.json().get("items", [])
            for c in contracts:
                if c.get("id") not in self._my_contract_ids:
                    self._my_contract_ids.append(c["id"])
                    _shared["contract_ids"].append(c["id"])

    @task(2)
    def view_contract_detail(self):
        if not self._my_contract_ids:
            return
        contract_id = random.choice(self._my_contract_ids)
        self.get_auth(
            f"/api/v1/contracts/{contract_id}",
            name="/api/v1/contracts/:id",
        )

    @task(1)
    def view_payment_summary(self):
        self.get_auth(
            "/api/v1/payments/summary",
            name="/api/v1/payments/summary",
        )

    @task(1)
    def view_transaction_history(self):
        self.get_auth(
            "/api/v1/payments/transactions",
            params={"page": 1, "page_size": 20},
            name="/api/v1/payments/transactions",
        )


# ══════════════════════════════════════════════════════════════════════════════
# 4. FREELANCER USER — searches & submits proposals
# ══════════════════════════════════════════════════════════════════════════════

class FreelancerUser(KaasbUser):
    """
    Freelancer flow: register → search jobs → submit proposals → work on contracts.
    Weight: 15% of traffic.
    """

    weight    = 15
    wait_time = between(1, 4)

    def on_start(self):
        if not self.register_and_login("freelancer"):
            raise StopUser()
        self._my_proposal_ids  = []
        self._viewed_job_ids   = []
        self._my_contract_ids  = []
        self._my_milestone_ids = []

    @task(4)
    def search_and_browse_jobs(self):
        params = self._gen.job_search_query()
        resp = self.client.get(
            "/api/v1/jobs",
            params=params,
            name="/api/v1/jobs [search]",
        )
        if resp.status_code == 200:
            jobs = resp.json().get("items", [])
            for j in jobs[:3]:
                if j.get("id") not in self._viewed_job_ids:
                    self._viewed_job_ids.append(j["id"])

    @task(3)
    def view_job_detail_and_decide(self):
        if not self._viewed_job_ids and not _shared["open_job_ids"]:
            return
        job_ids = self._viewed_job_ids or _shared["open_job_ids"]
        job_id  = random.choice(job_ids)
        resp = self.client.get(
            f"/api/v1/jobs/{job_id}",
            name="/api/v1/jobs/:id [detail]",
        )
        return resp

    @task(2)
    def submit_proposal(self):
        job_ids = _shared["open_job_ids"]
        if not job_ids:
            return
        job_id = random.choice(job_ids)
        # Get job details to craft a relevant proposal
        resp = self.client.get(
            f"/api/v1/jobs/{job_id}",
            name="/api/v1/jobs/:id [for proposal]",
        )
        if resp.status_code != 200:
            return
        job = resp.json()
        proposal_data = self._gen.proposal(job)
        resp2 = self.post_auth(
            f"/api/v1/proposals/jobs/{job_id}",
            json=proposal_data,
            name="/api/v1/proposals/jobs/:id [submit]",
        )
        if resp2.status_code == 201:
            pid = resp2.json().get("id")
            if pid:
                self._my_proposal_ids.append(pid)
                _shared["proposal_ids"].append(pid)

    @task(2)
    def view_my_proposals(self):
        resp = self.get_auth(
            "/api/v1/proposals/my",
            params={"page": 1, "page_size": 20},
            name="/api/v1/proposals/my",
        )
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            for p in items:
                if p.get("id") not in self._my_proposal_ids:
                    self._my_proposal_ids.append(p["id"])

    @task(1)
    def view_my_contracts(self):
        resp = self.get_auth(
            "/api/v1/contracts/my",
            params={"page": 1, "page_size": 20},
            name="/api/v1/contracts/my",
        )
        if resp.status_code == 200:
            for c in resp.json().get("items", []):
                if c.get("id") not in self._my_contract_ids:
                    self._my_contract_ids.append(c["id"])

    @task(1)
    def start_milestone_work(self):
        if not self._my_milestone_ids:
            return
        mid = random.choice(self._my_milestone_ids)
        self.post_auth(
            f"/api/v1/contracts/milestones/{mid}/start",
            json={},
            name="/api/v1/contracts/milestones/:id/start",
        )

    @task(1)
    def view_payment_summary(self):
        self.get_auth(
            "/api/v1/payments/summary",
            name="/api/v1/payments/summary",
        )


# ══════════════════════════════════════════════════════════════════════════════
# 5. CHAT USER — sends messages (real-time messaging load)
# ══════════════════════════════════════════════════════════════════════════════

class ChatUser(KaasbUser):
    """
    Simulates real-time messaging load.
    Sends messages, polls conversations.
    Weight: 5% of traffic.
    """

    weight    = 5
    wait_time = between(2, 8)

    def on_start(self):
        role = random.choice(["client", "freelancer"])
        if not self.register_and_login(role):
            raise StopUser()
        self._conversation_ids = []

    @task(2)
    def list_conversations(self):
        resp = self.get_auth(
            "/api/v1/messages/conversations",
            params={"page": 1, "page_size": 20},
            name="/api/v1/messages/conversations",
        )
        if resp.status_code == 200:
            for c in resp.json().get("conversations", []):
                if c.get("id") not in self._conversation_ids:
                    self._conversation_ids.append(c["id"])
                    _shared["conversation_ids"].append(c["id"])

    @task(3)
    def read_messages(self):
        conv_ids = self._conversation_ids or _shared["conversation_ids"]
        if not conv_ids:
            return
        conv_id = random.choice(conv_ids)
        self.get_auth(
            f"/api/v1/messages/conversations/{conv_id}",
            params={"page": 1, "page_size": 50},
            name="/api/v1/messages/conversations/:id [read]",
        )

    @task(4)
    def send_message(self):
        conv_ids = self._conversation_ids or _shared["conversation_ids"]
        if not conv_ids:
            return
        conv_id = random.choice(conv_ids)
        self.post_auth(
            f"/api/v1/messages/conversations/{conv_id}",
            json=self._gen.message(),
            name="/api/v1/messages/conversations/:id [send]",
        )

    @task(1)
    def check_notifications(self):
        self.get_auth(
            "/api/v1/notifications/unread-count",
            name="/api/v1/notifications/unread-count",
        )


# ══════════════════════════════════════════════════════════════════════════════
# Events: track stats on test completion
# ══════════════════════════════════════════════════════════════════════════════

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "="*60)
    print("  KAASB LOAD TEST COMPLETE")
    print("="*60)
    stats = environment.stats
    print(f"  Total requests:    {stats.total.num_requests:,}")
    print(f"  Total failures:    {stats.total.num_failures:,}")
    print(f"  Failure rate:      {stats.total.fail_ratio * 100:.2f}%")
    print(f"  Avg response time: {stats.total.avg_response_time:.0f}ms")
    print(f"  p95 response time: {stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"  p99 response time: {stats.total.get_response_time_percentile(0.99):.0f}ms")
    print(f"  Peak RPS:          {stats.total.current_rps:.1f}")
    print("="*60)

    # Pass/fail check
    fail_ratio = stats.total.fail_ratio
    p95        = stats.total.get_response_time_percentile(0.95)
    p99        = stats.total.get_response_time_percentile(0.99)

    passed = True
    if fail_ratio > 0.01:
        print(f"  FAIL: error rate {fail_ratio*100:.1f}% > 1% threshold")
        passed = False
    if p95 and p95 > 2000:
        print(f"  FAIL: p95 {p95:.0f}ms > 2000ms threshold")
        passed = False
    if p99 and p99 > 5000:
        print(f"  FAIL: p99 {p99:.0f}ms > 5000ms threshold")
        passed = False

    if passed:
        print("  RESULT: ✓ ALL THRESHOLDS PASSED")
    else:
        print("  RESULT: ✗ THRESHOLDS VIOLATED — see above")
    print("="*60 + "\n")
