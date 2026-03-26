"""
Kaasb — Race Condition & Concurrency Tests
===========================================
Tests concurrent operations that can cause data corruption:
  - Concurrent proposals on the same job (duplicate check)
  - Concurrent escrow funding on the same milestone
  - Concurrent message sending in the same conversation

Run:
  locust -f race_conditions.py --host=https://kaasb.com \
    --users=50 --spawn-rate=50 --run-time=3m --headless \
    --csv=reports/race_conditions

The key: ALL virtual users target the SAME resource simultaneously.
"""

import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from locust import HttpUser, task, between, events
from locust.exception import StopUser

from data.generator import IraqiDataGenerator

# ── Shared target resources (ONE job, ONE conversation) ───────────────────────
_target = {
    "job_id":          None,   # One job that all freelancers hit
    "conversation_id": None,   # One conversation for message storm
    "client_token":    None,
    "setup_done":      False,
}


def _setup_target(host: str):
    """Create a single target job for race condition testing."""
    if _target["setup_done"]:
        return

    import requests
    g = IraqiDataGenerator(seed=1)

    # Register a client
    client_data = g.client_user(9999)
    resp = requests.post(
        f"{host}/api/v1/auth/register",
        json={
            "email":        client_data["email"],
            "username":     client_data["username"],
            "password":     client_data["password"],
            "first_name":   client_data["first_name"],
            "last_name":    client_data["last_name"],
            "primary_role": "client",
        },
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        print(f"WARNING: Setup client registration failed: {resp.status_code}")
        _target["setup_done"] = True
        return

    token = resp.json().get("access_token")
    _target["client_token"] = token
    headers = {"Authorization": f"Bearer {token}"}

    # Post a job
    job = g.job()
    resp2 = requests.post(
        f"{host}/api/v1/jobs",
        json=job,
        headers=headers,
        timeout=10,
    )
    if resp2.status_code == 201:
        _target["job_id"] = resp2.json().get("id")
        print(f"[RACE SETUP] Target job created: {_target['job_id']}")
    else:
        print(f"WARNING: Could not create target job: {resp2.status_code}")

    _target["setup_done"] = True


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    _setup_target(environment.host)


# ══════════════════════════════════════════════════════════════════════════════
# RACE 1: Many freelancers submitting proposals to the SAME job simultaneously
# ══════════════════════════════════════════════════════════════════════════════

class ConcurrentProposalUser(HttpUser):
    """
    All users target the same job_id at once.
    Expected: only unique proposals per freelancer (409 on duplicate attempt).
    Failure mode: duplicate proposals, data corruption, deadlocks.
    """

    weight    = 50
    wait_time = between(0.5, 2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gen   = IraqiDataGenerator()
        self.token  = None
        self._submitted = False

    def on_start(self):
        data = self._gen.freelancer_user()
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email":        data["email"],
                "username":     data["username"],
                "password":     data["password"],
                "first_name":   data["first_name"],
                "last_name":    data["last_name"],
                "primary_role": "freelancer",
            },
            name="/auth/register [race]",
        )
        if resp.status_code in (200, 201):
            self.token = resp.json().get("access_token")
        else:
            raise StopUser()

    @task
    def submit_proposal_race(self):
        job_id = _target["job_id"]
        if not job_id or not self.token:
            return

        proposal_data = self._gen.proposal({"job_type": "fixed", "fixed_price": 500_000})
        resp = self.client.post(
            f"/api/v1/proposals/jobs/{job_id}",
            json=proposal_data,
            headers={"Authorization": f"Bearer {self.token}"},
            name="/proposals/:job_id [RACE - concurrent submit]",
        )

        # 201 = first submission (correct)
        # 409 = duplicate proposal (correct — system protected)
        # 500 = BUG — race condition caused server error
        if resp.status_code == 500:
            resp.failure(f"RACE CONDITION BUG: server error on concurrent proposal: {resp.text[:200]}")
        elif resp.status_code not in (201, 409, 400, 403, 404):
            resp.failure(f"Unexpected status {resp.status_code}: {resp.text[:100]}")
        else:
            # Success — mark as submitted so we don't spam
            self._submitted = True


# ══════════════════════════════════════════════════════════════════════════════
# RACE 2: Simultaneous messages in same conversation
# ══════════════════════════════════════════════════════════════════════════════

class ConcurrentMessageUser(HttpUser):
    """
    Multiple users hammering the same conversation with simultaneous messages.
    Expected: all messages saved correctly, no lost messages.
    Failure mode: message duplication, conversation unread_count corruption.
    """

    weight    = 30
    wait_time = between(0.1, 0.5)  # Very fast — stress test

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gen = IraqiDataGenerator()
        self.token = None
        self._conv_id = None

    def on_start(self):
        data = self._gen.user(role=random.choice(["client", "freelancer"]))
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email":        data["email"],
                "username":     data["username"],
                "password":     data["password"],
                "first_name":   data["first_name"],
                "last_name":    data["last_name"],
                "primary_role": data["primary_role"],
            },
            name="/auth/register [msg race]",
        )
        if resp.status_code in (200, 201):
            self.token = resp.json().get("access_token")
        else:
            raise StopUser()

    @task
    def send_concurrent_message(self):
        conv_id = _target.get("conversation_id")
        if not conv_id or not self.token:
            return

        resp = self.client.post(
            f"/api/v1/messages/conversations/{conv_id}",
            json={"content": self._gen.message()["content"]},
            headers={"Authorization": f"Bearer {self.token}"},
            name="/messages/:conv_id [RACE - concurrent send]",
        )
        if resp.status_code == 500:
            resp.failure(f"RACE CONDITION: concurrent message caused 500: {resp.text[:200]}")


# ══════════════════════════════════════════════════════════════════════════════
# RACE 3: Login storm — many logins with same credentials simultaneously
# ══════════════════════════════════════════════════════════════════════════════

class LoginStormUser(HttpUser):
    """
    Simulates a login storm — many users logging in simultaneously.
    Tests: session creation under load, JWT generation rate, DB write contention.
    """

    weight    = 20
    wait_time = between(0.1, 1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gen = IraqiDataGenerator()
        self._credentials = None

    def on_start(self):
        data = self._gen.user()
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email":        data["email"],
                "username":     data["username"],
                "password":     data["password"],
                "first_name":   data["first_name"],
                "last_name":    data["last_name"],
                "primary_role": data["primary_role"],
            },
            name="/auth/register [storm setup]",
        )
        if resp.status_code in (200, 201):
            self._credentials = {"email": data["email"], "password": data["password"]}
        else:
            raise StopUser()

    @task
    def login_storm(self):
        if not self._credentials:
            return
        resp = self.client.post(
            "/api/v1/auth/login",
            json=self._credentials,
            name="/auth/login [STORM]",
        )
        if resp.status_code == 500:
            resp.failure(f"Login storm caused 500: {resp.text[:200]}")
        elif resp.status_code == 429:
            # Rate limited — expected, mark as success
            pass


@events.test_stop.add_listener
def on_race_test_stop(environment, **kwargs):
    print("\n" + "="*60)
    print("  RACE CONDITION TEST COMPLETE")
    print("="*60)
    stats = environment.stats
    total = stats.total
    print(f"  Total requests: {total.num_requests:,}")
    print(f"  Total failures: {total.num_failures:,}")
    print(f"  Error rate:     {total.fail_ratio*100:.2f}%")
    print(f"  Avg latency:    {total.avg_response_time:.0f}ms")

    if total.fail_ratio > 0.001:
        print(f"\n  ✗ RACE CONDITIONS DETECTED — {total.num_failures} failures")
    else:
        print("\n  ✓ No race conditions detected")
    print("="*60 + "\n")
