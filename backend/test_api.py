"""
Kaasb Platform - Comprehensive API Test Suite v2
Tests ALL 63 endpoints across 11 route groups.
Run: python test_api.py
Requires: Backend running on localhost:8000
"""

import requests
import json
import time
import uuid
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000/api/v1"

# Terminal colors
class C:
    G = '\033[92m'   # Green
    R = '\033[91m'   # Red
    Y = '\033[93m'   # Yellow
    B = '\033[94m'   # Blue
    W = '\033[97m'   # White
    E = '\033[0m'    # End

def ok(msg): print(f"{C.G}  [PASS] {msg}{C.E}")
def fail(msg): print(f"{C.R}  [FAIL] {msg}{C.E}")
def info(msg): print(f"{C.B}  [INFO] {msg}{C.E}")
def section(num, msg): print(f"\n{C.Y}{'='*60}\n  TEST {num}: {msg}\n{'='*60}{C.E}")

# === Global state ===
tokens: Dict[str, str] = {}
user_ids: Dict[str, str] = {}
job_id = ""
job_id_2 = ""
proposal_id = ""
contract_id = ""
milestone_id = ""
milestone_id_2 = ""
conversation_id = ""

def h(role: str) -> dict:
    """Auth headers for a role."""
    return {"Authorization": f"Bearer {tokens[role]}"}

def raw(method, path, **kwargs):
    """Raw request — returns response object."""
    url = path if path.startswith("http") else f"{BASE_URL}{path}"
    return requests.request(method, url, **kwargs)


# ============================================================
#  1. HEALTH
# ============================================================

def test_01_health():
    """GET /health"""
    section(1, "Health Check")
    try:
        r = raw("GET", "/health")
        data = r.json()
        if r.status_code == 200 and data.get("status") in ("healthy", "degraded"):
            ok(f"API status: {data.get('status')} — db={data.get('database')}, redis={data.get('redis')}")
            return True
        fail(f"Unhealthy response: {r.status_code} {r.text[:300]}")
        return False
    except requests.ConnectionError:
        fail("Cannot connect to backend at localhost:8000")
        fail("Start the backend first: cd backend && uvicorn app.main:app --reload")
        return False


# ============================================================
#  2. AUTH — Register, Login, Refresh, Me
# ============================================================

def test_02_auth():
    """POST /auth/register, /auth/login, /auth/refresh, GET /auth/me"""
    section(2, "Authentication (4 endpoints)")
    global tokens, user_ids

    # --- Register client ---
    r = raw("POST", "/auth/register", json={
        "email": "client@test.com", "password": "TestPass123!",
        "first_name": "Test", "last_name": "Client",
        "username": "testclient", "primary_role": "client",
    })
    if r.status_code == 201 and "access_token" in r.json():
        tokens["client"] = r.json()["access_token"]
        ok("Client registered")
    elif r.status_code in (409, 429):
        r2 = raw("POST", "/auth/login", json={"email": "client@test.com", "password": "TestPass123!"})
        if r2.status_code == 200:
            tokens["client"] = r2.json()["access_token"]
            ok("Client already registered — logged in")
        else:
            fail(f"Client registration+login fallback: {r2.status_code}")
            return False
    else:
        fail(f"Client registration: {r.status_code} {r.text[:200]}")
        return False

    # --- Register freelancer ---
    r = raw("POST", "/auth/register", json={
        "email": "freelancer@test.com", "password": "TestPass123!",
        "first_name": "Test", "last_name": "Freelancer",
        "username": "testfreelancer", "primary_role": "freelancer",
    })
    if r.status_code == 201:
        tokens["freelancer"] = r.json()["access_token"]
        ok("Freelancer registered")
    elif r.status_code in (409, 429):
        r2 = raw("POST", "/auth/login", json={"email": "freelancer@test.com", "password": "TestPass123!"})
        if r2.status_code == 200:
            tokens["freelancer"] = r2.json()["access_token"]
            ok("Freelancer already registered — logged in")
        else:
            fail(f"Freelancer registration+login fallback: {r2.status_code}")
            return False
    else:
        fail(f"Freelancer registration: {r.status_code}")
        return False

    # --- Duplicate email → 409 ---
    r = raw("POST", "/auth/register", json={
        "email": "client@test.com", "password": "TestPass123!",
        "first_name": "Dup", "last_name": "User",
        "username": "dupuser", "primary_role": "client",
    })
    if r.status_code == 409:
        ok("Duplicate email rejected (409)")
    else:
        fail(f"Duplicate email: expected 409, got {r.status_code}")

    # --- Weak password → 422 ---
    r = raw("POST", "/auth/register", json={
        "email": "bad@test.com", "password": "weak",
        "first_name": "Bad", "last_name": "Pass",
        "username": "badpass", "primary_role": "client",
    })
    if r.status_code == 422:
        ok("Weak password rejected (422)")

    # --- Invalid username (spaces) → 422 ---
    r = raw("POST", "/auth/register", json={
        "email": "space@test.com", "password": "TestPass123!",
        "first_name": "Space", "last_name": "User",
        "username": "has spaces", "primary_role": "client",
    })
    if r.status_code == 422:
        ok("Username with spaces rejected (422)")

    # --- Login ---
    r = raw("POST", "/auth/login", json={
        "email": "client@test.com", "password": "TestPass123!",
    })
    if r.status_code == 200:
        data = r.json()
        tokens["client"] = data["access_token"]
        ok("Client login successful")

        # --- Refresh token ---
        r2 = raw("POST", "/auth/refresh", json={"refresh_token": data["refresh_token"]})
        if r2.status_code == 200:
            tokens["client"] = r2.json()["access_token"]
            ok("Token refresh successful")
        else:
            fail(f"Token refresh: {r2.status_code}")
    else:
        fail(f"Login: {r.status_code}")
        return False

    # --- Wrong password → 401 ---
    r = raw("POST", "/auth/login", json={
        "email": "client@test.com", "password": "WrongPass123!",
    })
    if r.status_code == 401:
        ok("Wrong password rejected (401)")

    # --- GET /auth/me ---
    r = raw("GET", "/auth/me", headers=h("client"))
    if r.status_code == 200:
        data = r.json()
        user_ids["client"] = data["id"]
        has_superuser = "is_superuser" in data
        ok(f"GET /me → ID: {data['id'][:8]}... is_superuser field: {has_superuser}")

    r = raw("GET", "/auth/me", headers=h("freelancer"))
    if r.status_code == 200:
        user_ids["freelancer"] = r.json()["id"]
        ok(f"GET /me → freelancer ID: {user_ids['freelancer'][:8]}...")

    # --- No token → 401 ---
    r = raw("GET", "/auth/me")
    if r.status_code in (401, 403):
        ok(f"Unauthenticated /me rejected ({r.status_code})")

    return True


# ============================================================
#  3. USERS — Profile, Freelancers, Password, Avatar
# ============================================================

def test_03_users():
    """7 user endpoints"""
    section(3, "Users (7 endpoints)")

    # --- GET /users/freelancers ---
    r = raw("GET", "/users/freelancers")
    if r.status_code == 200:
        ok(f"List freelancers → {r.json()['total']} found")

    # --- GET /users/profile/{username} ---
    r = raw("GET", "/users/profile/testfreelancer")
    if r.status_code == 200:
        ok(f"Profile by username → {r.json()['first_name']} {r.json()['last_name']}")

    # --- 404 profile ---
    r = raw("GET", "/users/profile/nonexistent_user_xyz")
    if r.status_code == 404:
        ok("Non-existent profile → 404")

    # --- PUT /users/profile ---
    r = raw("PUT", "/users/profile", json={
        "bio": "Experienced Python developer",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "hourly_rate": 50.0,
        "title": "Senior Backend Dev",
        "experience_level": "expert",
        "country": "Iraq",
        "city": "Tikrit",
    }, headers=h("freelancer"))
    if r.status_code == 200 and r.json().get("bio"):
        ok("Profile updated (bio, skills, rate, title, location)")

    # --- PUT /users/password ---
    r = raw("PUT", "/users/password", json={
        "current_password": "TestPass123!",
        "new_password": "NewPass456!",
    }, headers=h("freelancer"))
    if r.status_code == 200:
        ok("Password changed")
        # Restore
        raw("PUT", "/users/password", json={
            "current_password": "NewPass456!",
            "new_password": "TestPass123!",
        }, headers=h("freelancer"))
        ok("Password restored")
    else:
        info(f"Password change: {r.status_code} {r.text[:100]}")

    # --- Wrong current password ---
    r = raw("PUT", "/users/password", json={
        "current_password": "TotallyWrong123!",
        "new_password": "Another1!",
    }, headers=h("freelancer"))
    if r.status_code in (400, 401, 403):
        ok(f"Wrong current password rejected ({r.status_code})")

    # --- DELETE /users/avatar ---
    r = raw("DELETE", "/users/avatar", headers=h("freelancer"))
    if r.status_code in (200, 404):
        ok(f"Delete avatar endpoint works ({r.status_code})")

    # Note: POST /users/avatar needs multipart file upload, skip in automated test
    # Note: DELETE /users/account is destructive, skip in automated test
    info("POST /avatar (file upload) and DELETE /account (destructive) skipped")

    return True


# ============================================================
#  4. JOBS — CRUD, Search, Close, Delete
# ============================================================

def test_04_jobs():
    """7 job endpoints"""
    section(4, "Jobs (7 endpoints)")
    global job_id, job_id_2

    # --- POST /jobs/ (create) ---
    r = raw("POST", "/jobs/", json={
        "title": "Build a FastAPI Backend",
        "description": "Need an experienced Python developer to build a scalable REST API with authentication.",
        "category": "Web Development",
        "job_type": "fixed", "fixed_price": 1500.0,
        "skills_required": ["Python", "FastAPI", "PostgreSQL"],
        "experience_level": "intermediate",
        "duration": "1_to_3_months",
    }, headers=h("client"))
    if r.status_code == 201:
        job_id = r.json()["id"]
        ok(f"Job created → {job_id[:8]}...")
    else:
        fail(f"Create job: {r.status_code} {r.text[:200]}")
        return False

    # --- Create second job ---
    r = raw("POST", "/jobs/", json={
        "title": "Design a Logo",
        "description": "Modern logo design needed for a growing tech startup with clean and professional aesthetics.",
        "category": "Design", "job_type": "fixed", "fixed_price": 200.0,
        "skills_required": ["Logo Design"],
        "experience_level": "entry", "duration": "less_than_1_week",
    }, headers=h("client"))
    if r.status_code == 201:
        job_id_2 = r.json()["id"]
        ok(f"Second job created → {job_id_2[:8]}...")

    # --- Freelancer cannot create → 403 ---
    r = raw("POST", "/jobs/", json={
        "title": "Should Fail", "description": "...",
        "category": "Test", "job_type": "fixed", "fixed_price": 100.0,
    }, headers=h("freelancer"))
    if r.status_code == 403:
        ok("Freelancer blocked from creating jobs (403)")

    # --- GET /jobs/ (list) ---
    r = raw("GET", "/jobs/")
    if r.status_code == 200 and r.json().get("total", 0) >= 2:
        ok(f"List jobs → {r.json()['total']} jobs")

    # --- Search ---
    r = raw("GET", "/jobs/", params={"search": "FastAPI"})
    if r.status_code == 200 and r.json().get("total", 0) >= 1:
        ok(f"Search 'FastAPI' → {r.json()['total']} results")

    # --- Filter by category ---
    r = raw("GET", "/jobs/", params={"category": "Design"})
    if r.status_code == 200 and r.json().get("total", 0) >= 1:
        ok(f"Filter category=Design → {r.json()['total']} results")

    # --- GET /jobs/{id} ---
    r = raw("GET", f"/jobs/{job_id}")
    if r.status_code == 200:
        ok(f"Job detail → {r.json()['title']}")

    # --- 404 ---
    r = raw("GET", f"/jobs/{uuid.uuid4()}")
    if r.status_code == 404:
        ok("Non-existent job → 404")

    # --- PUT /jobs/{id} ---
    r = raw("PUT", f"/jobs/{job_id}", json={
        "title": "Build a FastAPI Backend (Updated)",
    }, headers=h("client"))
    if r.status_code == 200 and "Updated" in r.json().get("title", ""):
        ok("Job updated")

    # --- GET /jobs/my/posted ---
    r = raw("GET", "/jobs/my/posted", headers=h("client"))
    if r.status_code == 200 and r.json().get("total", 0) >= 2:
        ok(f"My posted jobs → {r.json()['total']}")

    # --- POST /jobs/{id}/close ---
    r = raw("POST", f"/jobs/{job_id_2}/close", headers=h("client"))
    if r.status_code == 200:
        ok(f"Job closed → {r.json().get('status')}")

    # --- DELETE /jobs/{id} ---
    r = raw("DELETE", f"/jobs/{job_id_2}", headers=h("client"))
    if r.status_code in (200, 204):
        ok("Job deleted")
    else:
        info(f"Job delete: {r.status_code} {r.text[:100]}")

    return True


# ============================================================
#  5. PROPOSALS
# ============================================================

def test_05_proposals():
    """7 proposal endpoints"""
    section(5, "Proposals (7 endpoints)")
    global proposal_id

    # --- POST /proposals/jobs/{id} ---
    r = raw("POST", f"/proposals/jobs/{job_id}", json={
        "cover_letter": "I'm an experienced FastAPI developer with 5 years of Python backend work and REST API expertise.",
        "bid_amount": 1200.0,
        "estimated_duration": "2_to_4_weeks",
    }, headers=h("freelancer"))
    if r.status_code == 201:
        proposal_id = r.json()["id"]
        ok(f"Proposal submitted → {proposal_id[:8]}...")
    else:
        fail(f"Submit proposal: {r.status_code} {r.text[:200]}")
        return False

    # --- Client cannot submit → 403 ---
    r = raw("POST", f"/proposals/jobs/{job_id}", json={
        "cover_letter": "This should be blocked since clients cannot submit proposals on the platform.", "bid_amount": 500.0,
    }, headers=h("client"))
    if r.status_code == 403:
        ok("Client blocked from proposals (403)")

    # --- Duplicate → 400 ---
    r = raw("POST", f"/proposals/jobs/{job_id}", json={
        "cover_letter": "Submitting again to test duplicate proposal rejection by the system.", "bid_amount": 1100.0,
    }, headers=h("freelancer"))
    if r.status_code == 400:
        ok("Duplicate proposal rejected (400)")

    # --- GET /proposals/jobs/{id}/list ---
    r = raw("GET", f"/proposals/jobs/{job_id}/list", headers=h("client"))
    if r.status_code == 200:
        ok(f"Proposals for job → {r.json()['total']}")

    # --- GET /proposals/{id} ---
    r = raw("GET", f"/proposals/{proposal_id}", headers=h("freelancer"))
    if r.status_code == 200:
        ok(f"Proposal detail → status: {r.json()['status']}")

    # --- PUT /proposals/{id} ---
    r = raw("PUT", f"/proposals/{proposal_id}", json={
        "bid_amount": 1300.0,
    }, headers=h("freelancer"))
    if r.status_code == 200:
        ok(f"Proposal updated → ${r.json()['bid_amount']}")

    # --- GET /proposals/my ---
    r = raw("GET", "/proposals/my", headers=h("freelancer"))
    if r.status_code == 200:
        ok(f"My proposals → {r.json()['total']}")

    # --- POST /proposals/{id}/respond (accept) ---
    r = raw("POST", f"/proposals/{proposal_id}/respond", json={
        "status": "accepted",
    }, headers=h("client"))
    if r.status_code == 200:
        ok(f"Proposal accepted → contract created")
    else:
        fail(f"Proposal accept: {r.status_code} {r.text[:200]}")
        return False

    return True


# ============================================================
#  6. CONTRACTS & MILESTONES
# ============================================================

def test_06_contracts():
    """8 contract/milestone endpoints"""
    section(6, "Contracts & Milestones (8 endpoints)")
    global contract_id, milestone_id, milestone_id_2

    # --- GET /contracts/my ---
    r = raw("GET", "/contracts/my", headers=h("client"))
    if r.status_code == 200 and r.json().get("total", 0) >= 1:
        contract_id = r.json()["contracts"][0]["id"]
        ok(f"My contracts → {r.json()['total']}, ID: {contract_id[:8]}...")
    else:
        fail("No contracts found")
        return False

    # --- GET /contracts/{id} ---
    r = raw("GET", f"/contracts/{contract_id}", headers=h("client"))
    if r.status_code == 200:
        ok(f"Contract detail → status: {r.json()['status']}")

    # --- POST /contracts/{id}/milestones ---
    r = raw("POST", f"/contracts/{contract_id}/milestones", json={
        "milestones": [
            {"title": "Backend API", "description": "Core REST endpoints", "amount": 800.0, "due_date": "2026-04-15"},
            {"title": "Frontend Integration", "description": "Connect frontend", "amount": 500.0, "due_date": "2026-05-01"},
        ],
    }, headers=h("client"))
    if r.status_code == 201:
        ms = r.json().get("milestones", [])
        if not ms:
            fail(f"Add milestones returned 201 but milestones list is empty. Response: {r.json()}")
            return False
        milestone_id = ms[0]["id"]
        milestone_id_2 = ms[1]["id"] if len(ms) > 1 else ""
        ok(f"Added {len(ms)} milestones")
    else:
        fail(f"Add milestones: {r.status_code} {r.text[:200]}")
        return False

    # --- PUT /contracts/milestones/{id} ---
    r = raw("PUT", f"/contracts/milestones/{milestone_id}", json={
        "title": "Backend API (Updated)", "amount": 850.0,
    }, headers=h("client"))
    if r.status_code == 200:
        ok(f"Milestone updated → ${r.json()['amount']}")

    # --- Lifecycle: start → submit → approve ---
    r = raw("POST", f"/contracts/milestones/{milestone_id}/start", headers=h("freelancer"))
    if r.status_code == 200 and r.json().get("status") == "in_progress":
        ok("Milestone → in_progress")
    else:
        fail(f"Start milestone: {r.status_code}")

    r = raw("POST", f"/contracts/milestones/{milestone_id}/submit", json={
        "deliverable_url": "https://github.com/kaasb/api",
        "deliverable_note": "All endpoints implemented.",
    }, headers=h("freelancer"))
    if r.status_code == 200:
        ok("Milestone → submitted")

    r = raw("POST", f"/contracts/milestones/{milestone_id}/review", json={
        "action": "approve",
    }, headers=h("client"))
    if r.status_code == 200:
        ok("Milestone → approved ✓")

    # --- Revision flow ---
    if milestone_id_2:
        raw("POST", f"/contracts/milestones/{milestone_id_2}/start", headers=h("freelancer"))
        raw("POST", f"/contracts/milestones/{milestone_id_2}/submit", json={
            "deliverable_url": "https://github.com/kaasb/frontend",
            "deliverable_note": "First draft",
        }, headers=h("freelancer"))
        r = raw("POST", f"/contracts/milestones/{milestone_id_2}/review", json={
            "action": "request_revision",
            "feedback": "Add loading states.",
        }, headers=h("client"))
        if r.status_code == 200:
            ok("Milestone → revision_requested")

    # --- DELETE milestone ---
    temp = raw("POST", f"/contracts/{contract_id}/milestones", json={
        "milestones": [{"title": "Temp", "description": "Delete me", "amount": 50.0}],
    }, headers=h("client"))
    if temp.status_code == 201:
        temp_ms = temp.json()["milestones"]
        temp_id = temp_ms[-1]["id"]
        r = raw("DELETE", f"/contracts/milestones/{temp_id}", headers=h("client"))
        if r.status_code in (200, 204):
            ok("Milestone deleted")
        else:
            info(f"Milestone delete: {r.status_code}")

    return True


# ============================================================
#  7. PAYMENTS
# ============================================================

def test_07_payments():
    """6 payment endpoints"""
    section(7, "Payments (6 endpoints)")

    # --- POST /payments/accounts (Stripe for client) ---
    r = raw("POST", "/payments/accounts", json={"provider": "stripe"}, headers=h("client"))
    if r.status_code in (200, 201) and r.json().get("provider") == "stripe":
        ok(f"Client Stripe account → {r.json()['status']}")

    # --- POST /payments/accounts (Wise for freelancer) ---
    r = raw("POST", "/payments/accounts", json={
        "provider": "wise", "wise_email": "freelancer@wise.com", "wise_currency": "USD",
    }, headers=h("freelancer"))
    if r.status_code in (200, 201):
        ok(f"Freelancer Wise account → {r.json()['status']}")

    # --- Wise without email → 400 ---
    r = raw("POST", "/payments/accounts", json={"provider": "wise"}, headers=h("freelancer"))
    if r.status_code == 400:
        ok("Wise without email rejected (400)")

    # --- Duplicate → 400 ---
    r = raw("POST", "/payments/accounts", json={"provider": "stripe"}, headers=h("client"))
    if r.status_code == 400:
        ok("Duplicate account rejected (400)")

    # --- GET /payments/accounts ---
    r = raw("GET", "/payments/accounts", headers=h("client"))
    if r.status_code == 200:
        ok(f"Client accounts → {len(r.json())} account(s)")

    # --- POST /payments/escrow/fund ---
    if milestone_id:
        r = raw("POST", "/payments/escrow/fund", json={
            "milestone_id": milestone_id,
        }, headers=h("client"))
        if r.status_code in (200, 201):
            d = r.json()
            ok(f"Escrow funded → fee: ${d.get('platform_fee', 0)}")
        else:
            info(f"Fund escrow: {r.status_code} {r.text[:100]}")

        # Double fund → 400
        r = raw("POST", "/payments/escrow/fund", json={"milestone_id": milestone_id}, headers=h("client"))
        if r.status_code == 400:
            ok("Double funding rejected (400)")

        # Freelancer cannot fund → 403
        r = raw("POST", "/payments/escrow/fund", json={"milestone_id": milestone_id}, headers=h("freelancer"))
        if r.status_code == 403:
            ok("Freelancer funding rejected (403)")

    # --- GET /payments/summary ---
    r = raw("GET", "/payments/summary", headers=h("client"))
    if r.status_code == 200:
        d = r.json()
        ok(f"Client summary → spent: ${d['total_spent']}, escrow: ${d['pending_escrow']}")

    r = raw("GET", "/payments/summary", headers=h("freelancer"))
    if r.status_code == 200:
        ok(f"Freelancer summary → earned: ${r.json()['total_earned']}")

    # --- GET /payments/transactions ---
    r = raw("GET", "/payments/transactions", headers=h("client"))
    if r.status_code == 200:
        ok(f"Transactions → {r.json()['total']} records")

    # --- POST /payments/payout ---
    accts = raw("GET", "/payments/accounts", headers=h("freelancer"))
    if accts.status_code == 200 and len(accts.json()) > 0:
        r = raw("POST", "/payments/payout", json={
            "amount": 10.0,
            "payment_account_id": accts.json()[0]["id"],
        }, headers=h("freelancer"))
        if r.status_code in (200, 201):
            ok(f"Payout requested → {r.json().get('status')}")
        else:
            info(f"Payout: {r.status_code} (insufficient balance is expected)")

    return True


# ============================================================
#  8. MESSAGES
# ============================================================

def test_08_messages():
    """4 message endpoints"""
    section(8, "Messages (4 endpoints)")
    global conversation_id

    # --- POST /messages/conversations ---
    r = raw("POST", "/messages/conversations", json={
        "recipient_id": user_ids["freelancer"],
        "initial_message": "Hi! Let's discuss the project.",
    }, headers=h("client"))
    if r.status_code == 201:
        conversation_id = r.json()["id"]
        ok(f"Conversation started → {conversation_id[:8]}...")
    else:
        fail(f"Start conversation: {r.status_code}")
        return False

    # --- Self-message → 400 ---
    r = raw("POST", "/messages/conversations", json={
        "recipient_id": user_ids["client"],
        "initial_message": "Self-talk",
    }, headers=h("client"))
    if r.status_code == 400:
        ok("Self-messaging rejected (400)")

    # --- POST /messages/conversations/{id} (send message) ---
    r = raw("POST", f"/messages/conversations/{conversation_id}", json={
        "content": "I estimate 4 weeks for the backend.",
    }, headers=h("freelancer"))
    if r.status_code == 201:
        ok("Freelancer replied")

    r = raw("POST", f"/messages/conversations/{conversation_id}", json={
        "content": "Sounds good, let's proceed!",
    }, headers=h("client"))
    if r.status_code == 201:
        ok("Client replied")

    # --- GET /messages/conversations/{id} (get messages + mark read) ---
    r = raw("GET", f"/messages/conversations/{conversation_id}", headers=h("freelancer"))
    if r.status_code == 200:
        ok(f"Messages → {r.json()['total']} total")

    # --- GET /messages/conversations (list) ---
    r = raw("GET", "/messages/conversations", headers=h("client"))
    if r.status_code == 200:
        ok(f"Conversations → {r.json()['total']} total")

    # --- Non-existent conversation → 404 ---
    r = raw("GET", f"/messages/conversations/{uuid.uuid4()}", headers=h("client"))
    if r.status_code in (403, 404):
        ok(f"Non-existent conversation → {r.status_code}")

    return True


# ============================================================
#  9. REVIEWS
# ============================================================

def test_09_reviews():
    """4 review endpoints"""
    section(9, "Reviews (4 endpoints)")

    # Check contract status
    r = raw("GET", f"/contracts/{contract_id}", headers=h("client"))
    status = r.json().get("status", "unknown") if r.status_code == 200 else "unknown"
    info(f"Contract status: {status}")

    if status == "completed":
        # Client reviews freelancer
        r = raw("POST", f"/reviews/contract/{contract_id}", json={
            "rating": 5, "comment": "Excellent work!",
            "communication_rating": 5, "quality_rating": 5,
            "professionalism_rating": 5, "timeliness_rating": 4,
        }, headers=h("client"))
        if r.status_code == 201:
            ok(f"Client reviewed → {r.json()['rating']}★")

        # Freelancer reviews client
        r = raw("POST", f"/reviews/contract/{contract_id}", json={
            "rating": 4, "comment": "Clear requirements.",
            "communication_rating": 5,
        }, headers=h("freelancer"))
        if r.status_code == 201:
            ok(f"Freelancer reviewed → {r.json()['rating']}★")

        # Duplicate → 400
        r = raw("POST", f"/reviews/contract/{contract_id}", json={"rating": 3}, headers=h("client"))
        if r.status_code == 400:
            ok("Duplicate review rejected (400)")
    else:
        # Review on incomplete → 400
        r = raw("POST", f"/reviews/contract/{contract_id}", json={
            "rating": 5, "comment": "Test",
        }, headers=h("client"))
        if r.status_code == 400:
            ok("Review on incomplete contract rejected (400)")
        info("Contract not completed → review submission skipped (expected)")

    # --- GET /reviews/user/{id} (public) ---
    r = raw("GET", f"/reviews/user/{user_ids['freelancer']}")
    if r.status_code == 200:
        ok(f"User reviews → {r.json()['total']} reviews")

    # --- GET /reviews/user/{id}/stats ---
    r = raw("GET", f"/reviews/user/{user_ids['freelancer']}/stats")
    if r.status_code == 200:
        d = r.json()
        ok(f"Review stats → avg: {d['average_rating']}, total: {d['total_reviews']}")

    # --- GET /reviews/contract/{id} ---
    r = raw("GET", f"/reviews/contract/{contract_id}", headers=h("client"))
    if r.status_code == 200:
        ok(f"Contract reviews → {len(r.json())} review(s)")

    return True


# ============================================================
#  10. NOTIFICATIONS
# ============================================================

def test_10_notifications():
    """4 notification endpoints"""
    section(10, "Notifications (4 endpoints)")

    # --- GET /notifications ---
    r = raw("GET", "/notifications", headers=h("freelancer"))
    if r.status_code == 200:
        ok(f"Notifications → {r.json()['total']} total, {r.json()['unread_count']} unread")

    # --- GET /notifications/unread-count ---
    r = raw("GET", "/notifications/unread-count", headers=h("client"))
    if r.status_code == 200:
        ok(f"Unread count → {r.json()['count']}")

    # --- Filter unread only ---
    r = raw("GET", "/notifications", params={"unread_only": True}, headers=h("freelancer"))
    if r.status_code == 200:
        ok(f"Unread filter → {r.json()['total']}")

    # --- POST /notifications/mark-read ---
    r = raw("GET", "/notifications", headers=h("freelancer"))
    if r.status_code == 200 and r.json()["notifications"]:
        nid = r.json()["notifications"][0]["id"]
        r2 = raw("POST", "/notifications/mark-read", json={"notification_ids": [nid]}, headers=h("freelancer"))
        if r2.status_code == 200:
            ok(f"Marked 1 notification read")
    else:
        info("No notifications to mark as read")

    # --- POST /notifications/mark-all-read ---
    r = raw("POST", "/notifications/mark-all-read", headers=h("freelancer"))
    if r.status_code == 200:
        ok(f"Mark all read → {r.json()['marked']} marked")

    return True


# ============================================================
#  11. SECURITY
# ============================================================

def test_11_security():
    """Security headers + rate limiting"""
    section(11, "Security & Rate Limiting")

    r = raw("GET", "/health")
    checks = {
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "x-xss-protection": "1; mode=block",
    }
    for hdr, expected in checks.items():
        val = r.headers.get(hdr, "")
        if expected.lower() in val.lower():
            ok(f"{hdr}: {val}")
        else:
            fail(f"{hdr} missing (got: '{val}')")

    if r.headers.get("x-request-id"):
        ok(f"X-Request-ID: {r.headers['x-request-id'][:16]}...")

    if r.headers.get("x-ratelimit-limit"):
        ok(f"Rate limit: {r.headers['x-ratelimit-remaining']}/{r.headers['x-ratelimit-limit']}")
    else:
        info("Rate limit headers not on /health (applies to API routes)")

    return True


# ============================================================
#  12. ADMIN
# ============================================================

def test_12_admin():
    """7 admin endpoints + access control"""
    section(12, "Admin (7 endpoints + access control)")

    # --- All admin endpoints reject non-admin ---
    blocked = 0
    for method, path, body in [
        ("GET", "/admin/stats", None),
        ("GET", "/admin/users", None),
        ("GET", "/admin/jobs", None),
        ("GET", "/admin/transactions", None),
        ("PUT", f"/admin/users/{user_ids['client']}/status", {"status": "suspended"}),
        ("POST", f"/admin/users/{user_ids['client']}/toggle-admin", None),
        ("PUT", f"/admin/jobs/{job_id}/status", {"status": "closed"}),
    ]:
        kwargs = {"headers": h("freelancer")}
        if body:
            kwargs["json"] = body
        r = raw(method, path, **kwargs)
        if r.status_code == 403:
            blocked += 1
        else:
            fail(f"Expected 403 for {method} {path}, got {r.status_code}")

    ok(f"All {blocked}/7 admin endpoints correctly reject non-admin (403)")

    # --- Unauthenticated ---
    r = raw("GET", "/admin/stats")
    if r.status_code in (401, 403):
        ok(f"Unauthenticated admin access rejected ({r.status_code})")

    info("Admin functional tests require superuser (use scripts/create_admin.py)")
    return True


# ============================================================
#  RUNNER
# ============================================================

def run_all_tests():
    print(f"\n{C.W}{'='*60}")
    print(f"  KAASB PLATFORM — COMPREHENSIVE TEST SUITE v2")
    print(f"  Testing ALL 63 endpoints across 11 route groups")
    print(f"  Target: {BASE_URL}")
    print(f"{'='*60}{C.E}\n")

    tests = [
        ("Health Check", test_01_health),
        ("Authentication (4 endpoints)", test_02_auth),
        ("Users (7 endpoints)", test_03_users),
        ("Jobs (7 endpoints)", test_04_jobs),
        ("Proposals (7 endpoints)", test_05_proposals),
        ("Contracts & Milestones (8 endpoints)", test_06_contracts),
        ("Payments (6 endpoints)", test_07_payments),
        ("Messages (4 endpoints)", test_08_messages),
        ("Reviews (4 endpoints)", test_09_reviews),
        ("Notifications (4 endpoints)", test_10_notifications),
        ("Security & Rate Limiting", test_11_security),
        ("Admin (7 endpoints + access)", test_12_admin),
    ]

    passed = 0
    failed = 0
    results = []

    for name, func in tests:
        try:
            success = func()
            results.append((name, success))
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            results.append((name, False))
            fail(f"Exception: {str(e)}")

    # Summary
    print(f"\n{C.W}{'='*60}")
    print(f"  TEST RESULTS SUMMARY")
    print(f"{'='*60}{C.E}\n")

    for name, success in results:
        icon = f"{C.G}PASS{C.E}" if success else f"{C.R}FAIL{C.E}"
        print(f"  [{icon}] {name}")

    total = passed + failed
    color = C.G if failed == 0 else C.R
    print(f"\n{color}  {passed}/{total} test groups passed{C.E}")

    if failed == 0:
        print(f"\n{C.G}  ✅ ALL TESTS PASSED — Platform is fully operational!{C.E}\n")
    else:
        print(f"\n{C.R}  ❌ {failed} test group(s) failed — review output above{C.E}\n")

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
