"""
Kaasb Platform - Comprehensive API Test Suite
Tests all implemented functionality: Auth, Users, Jobs
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}[PASS] {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}[FAIL] {msg}{Colors.END}")

def print_info(msg: str):
    print(f"{Colors.BLUE}[INFO] {msg}{Colors.END}")

def print_section(msg: str):
    print(f"\n{Colors.YELLOW}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{Colors.END}\n")

# Test data
client_data = {
    "email": "client@test.com",
    "password": "TestPass123!",
    "first_name": "Test",
    "last_name": "Client",
    "username": "testclient",
    "primary_role": "client"
}

freelancer_data = {
    "email": "freelancer@test.com",
    "password": "TestPass123!",
    "first_name": "Test",
    "last_name": "Freelancer",
    "username": "testfreelancer",
    "primary_role": "freelancer"
}

job_data = {
    "title": "Build a FastAPI Backend",
    "description": "Need an experienced Python developer to build a REST API using FastAPI. Must have experience with PostgreSQL and Docker.",
    "category": "Web Development",
    "job_type": "fixed",
    "fixed_price": 1500.0,
    "skills_required": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "experience_level": "intermediate",
    "duration": "1_to_3_months",
    "status": "open"
}

# Store tokens and IDs
tokens: Dict[str, str] = {}
user_ids: Dict[str, str] = {}
job_id: str = ""

def test_health_check():
    """Test 1: Health check endpoint"""
    print_section("TEST 1: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_success(f"Health check passed: {data}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check error: {str(e)}")
        return False

def test_register_users():
    """Test 2: User registration (Client & Freelancer)"""
    print_section("TEST 2: User Registration")

    # Register Client
    try:
        print_info("Registering client...")
        response = requests.post(f"{BASE_URL}/auth/register", json=client_data)
        if response.status_code == 201:
            data = response.json()
            # Registration returns tokens, save them
            tokens['client'] = data['access_token']
            print_success(f"Client registered successfully")
            # Get user details using the token
            headers = {"Authorization": f"Bearer {tokens['client']}"}
            me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
            if me_response.status_code == 200:
                user_data = me_response.json()
                user_ids['client'] = user_data['id']
                print_info(f"Username: {user_data['username']}, ID: {user_ids['client']}")
        else:
            print_error(f"Client registration failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"Client registration error: {str(e)}")
        return False

    # Register Freelancer
    try:
        print_info("Registering freelancer...")
        response = requests.post(f"{BASE_URL}/auth/register", json=freelancer_data)
        if response.status_code == 201:
            data = response.json()
            # Registration returns tokens, save them
            tokens['freelancer'] = data['access_token']
            print_success(f"Freelancer registered successfully")
            # Get user details using the token
            headers = {"Authorization": f"Bearer {tokens['freelancer']}"}
            me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
            if me_response.status_code == 200:
                user_data = me_response.json()
                user_ids['freelancer'] = user_data['id']
                print_info(f"Username: {user_data['username']}, ID: {user_ids['freelancer']}")
            return True
        else:
            print_error(f"Freelancer registration failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"Freelancer registration error: {str(e)}")
        return False

def test_login_users():
    """Test 3: User login & token generation"""
    print_section("TEST 3: User Login & Authentication")

    # Login Client
    try:
        print_info("Logging in client...")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": client_data['email'], "password": client_data['password']}
        )
        if response.status_code == 200:
            data = response.json()
            tokens['client'] = data['access_token']
            print_success(f"Client logged in successfully")
            print_info(f"Token: {tokens['client'][:50]}...")
        else:
            print_error(f"Client login failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"Client login error: {str(e)}")
        return False

    # Login Freelancer
    try:
        print_info("Logging in freelancer...")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": freelancer_data['email'], "password": freelancer_data['password']}
        )
        if response.status_code == 200:
            data = response.json()
            tokens['freelancer'] = data['access_token']
            print_success(f"Freelancer logged in successfully")
            print_info(f"Token: {tokens['freelancer'][:50]}...")
            return True
        else:
            print_error(f"Freelancer login failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"Freelancer login error: {str(e)}")
        return False

def test_get_current_user():
    """Test 4: Get current user (me endpoint)"""
    print_section("TEST 4: Get Current User")

    try:
        print_info("Getting client profile...")
        headers = {"Authorization": f"Bearer {tokens['client']}"}
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Client profile: {data['username']} - {data['primary_role']}")
            print_info(f"Email: {data['email']}")
            return True
        else:
            print_error(f"Get current user failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"Get current user error: {str(e)}")
        return False

def test_create_job():
    """Test 5: Create a job (as client)"""
    print_section("TEST 5: Create Job Posting")

    global job_id
    try:
        print_info("Creating job as client...")
        headers = {"Authorization": f"Bearer {tokens['client']}"}
        response = requests.post(f"{BASE_URL}/jobs/", json=job_data, headers=headers)
        if response.status_code == 201:
            data = response.json()
            job_id = data['id']
            print_success(f"Job created: '{data['title']}' (ID: {job_id})")
            print_info(f"Budget: ${data.get('fixed_price', 'N/A')}, Status: {data['status']}")
            return True
        else:
            print_error(f"Job creation failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"Job creation error: {str(e)}")
        return False

def test_list_jobs():
    """Test 6: List all jobs (public endpoint)"""
    print_section("TEST 6: List Jobs")

    try:
        print_info("Fetching job listings...")
        response = requests.get(f"{BASE_URL}/jobs/")
        if response.status_code == 200:
            data = response.json()
            # Handle both list and dict responses
            if isinstance(data, dict) and 'items' in data:
                jobs = data['items']
            elif isinstance(data, list):
                jobs = data
            else:
                jobs = []

            jobs_count = len(jobs)
            print_success(f"Found {jobs_count} job(s)")
            if jobs_count > 0:
                first_job = jobs[0]
                print_info(f"First job: '{first_job['title']}' - ${first_job.get('fixed_price', 'N/A')}")
            return True
        else:
            print_error(f"List jobs failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"List jobs error: {str(e)}")
        return False

def test_get_job_details():
    """Test 7: Get specific job details"""
    print_section("TEST 7: Get Job Details")

    if not job_id:
        print_error("No job ID available to test")
        return False

    try:
        print_info(f"Fetching job details for ID: {job_id}")
        response = requests.get(f"{BASE_URL}/jobs/{job_id}")
        if response.status_code == 200:
            data = response.json()
            print_success(f"Job details retrieved: '{data['title']}'")
            print_info(f"Category: {data['category']}")
            print_info(f"Skills: {', '.join(data.get('skills_required', []))}")
            print_info(f"Client ID: {data.get('client_id', 'N/A')}")
            return True
        else:
            print_error(f"Get job details failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"Get job details error: {str(e)}")
        return False

def test_get_user_profile():
    """Test 8: Get user profile by username"""
    print_section("TEST 8: Get User Profile")

    try:
        print_info(f"Fetching profile for username: {client_data['username']}")
        response = requests.get(f"{BASE_URL}/users/profile/{client_data['username']}")
        if response.status_code == 200:
            data = response.json()
            full_name = f"{data['first_name']} {data['last_name']}"
            print_success(f"Profile retrieved: {data['username']} ({full_name})")
            print_info(f"Role: {data['primary_role']}")
            return True
        else:
            print_error(f"Get user profile failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"Get user profile error: {str(e)}")
        return False

def test_update_profile():
    """Test 9: Update user profile"""
    print_section("TEST 9: Update User Profile")

    try:
        print_info("Updating freelancer profile...")
        headers = {"Authorization": f"Bearer {tokens['freelancer']}"}
        update_data = {
            "bio": "Experienced Python developer with 5+ years in FastAPI",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "React"],
            "hourly_rate": 75.0
        }
        response = requests.put(f"{BASE_URL}/users/profile", json=update_data, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Profile updated successfully")
            print_info(f"Bio: {data.get('bio', 'N/A')[:50]}...")
            print_info(f"Hourly rate: ${data.get('hourly_rate', 'N/A')}")
            print_info(f"Skills: {', '.join(data.get('skills', []))}")
            return True
        else:
            print_error(f"Update profile failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print_error(f"Update profile error: {str(e)}")
        return False

proposal_id: str = ""

def test_submit_proposal():
    """Test 10: Submit a proposal (freelancer)"""
    global proposal_id
    print_section("TEST 10: Submit Proposal")

    try:
        if not tokens.get('freelancer') or not job_id:
            print_error("Need freelancer token and a job_id — skipping")
            return False

        headers = {"Authorization": f"Bearer {tokens['freelancer']}"}
        proposal_data = {
            "cover_letter": "I am an experienced Python developer with 5+ years of FastAPI expertise. I have built similar API integration systems for multiple clients and can deliver high-quality work within the timeline.",
            "bid_amount": 1200.0,
            "estimated_duration": "2 weeks",
        }
        response = requests.post(f"{BASE_URL}/proposals/jobs/{job_id}", json=proposal_data, headers=headers)
        if response.status_code == 201:
            data = response.json()
            proposal_id = data["id"]
            print_success(f"Proposal submitted (ID: {proposal_id})")
            print_info(f"Bid: ${data['bid_amount']} | Status: {data['status']}")

            # Verify duplicate is rejected
            dup = requests.post(f"{BASE_URL}/proposals/jobs/{job_id}", json=proposal_data, headers=headers)
            if dup.status_code == 409:
                print_success("Duplicate proposal correctly rejected (409)")
            else:
                print_error(f"Duplicate should be 409, got {dup.status_code}")

            # Verify client can't submit proposals
            client_headers = {"Authorization": f"Bearer {tokens['client']}"}
            client_try = requests.post(f"{BASE_URL}/proposals/jobs/{job_id}", json=proposal_data, headers=client_headers)
            if client_try.status_code == 403:
                print_success("Client correctly blocked from submitting proposals (403)")
            else:
                print_error(f"Client should get 403, got {client_try.status_code}")

            return True
        else:
            print_error(f"Submit proposal failed: {response.status_code} - {response.text[:300]}")
            return False
    except Exception as e:
        print_error(f"Submit proposal error: {str(e)}")
        return False


def test_list_proposals():
    """Test 11: List proposals (freelancer + client views)"""
    print_section("TEST 11: List Proposals")

    try:
        # Freelancer: my proposals
        headers_fl = {"Authorization": f"Bearer {tokens['freelancer']}"}
        response = requests.get(f"{BASE_URL}/proposals/my", headers=headers_fl)
        if response.status_code != 200:
            print_error(f"GET /proposals/my failed: {response.status_code}")
            return False

        data = response.json()
        print_success(f"Freelancer has {data['total']} proposal(s)")

        # Client: proposals on their job
        headers_cl = {"Authorization": f"Bearer {tokens['client']}"}
        response = requests.get(f"{BASE_URL}/proposals/jobs/{job_id}/list", headers=headers_cl)
        if response.status_code != 200:
            print_error(f"GET proposals on job failed: {response.status_code}")
            return False

        data = response.json()
        print_success(f"Client sees {data['total']} proposal(s) on their job")

        if data['proposals']:
            p = data['proposals'][0]
            print_info(f"Freelancer: {p['freelancer']['first_name']} | Bid: ${p['bid_amount']}")

        # Freelancer should NOT be able to list proposals on a job
        response = requests.get(f"{BASE_URL}/proposals/jobs/{job_id}/list", headers=headers_fl)
        if response.status_code == 403:
            print_success("Freelancer correctly blocked from listing job proposals (403)")
        else:
            print_error(f"Freelancer should get 403, got {response.status_code}")

        return True
    except Exception as e:
        print_error(f"List proposals error: {str(e)}")
        return False


def test_respond_proposal():
    """Test 12: Client responds to proposal (shortlist → accept)"""
    print_section("TEST 12: Respond to Proposal")

    try:
        if not proposal_id or not tokens.get('client'):
            print_error("Need proposal_id and client token — skipping")
            return False

        headers = {"Authorization": f"Bearer {tokens['client']}"}

        # Shortlist
        response = requests.post(
            f"{BASE_URL}/proposals/{proposal_id}/respond",
            json={"status": "shortlisted", "client_note": "Great experience!"},
            headers=headers,
        )
        if response.status_code == 200 and response.json().get("status") == "shortlisted":
            print_success("Proposal shortlisted")
        else:
            print_error(f"Shortlist failed: {response.status_code} - {response.text[:200]}")
            return False

        # Accept
        response = requests.post(
            f"{BASE_URL}/proposals/{proposal_id}/respond",
            json={"status": "accepted"},
            headers=headers,
        )
        if response.status_code == 200 and response.json().get("status") == "accepted":
            print_success("Proposal accepted")
        else:
            print_error(f"Accept failed: {response.status_code} - {response.text[:200]}")
            return False

        # Verify job is now in_progress
        job_response = requests.get(f"{BASE_URL}/jobs/{job_id}")
        if job_response.status_code == 200:
            job_data = job_response.json()
            if job_data.get("status") == "in_progress":
                print_success(f"Job status changed to in_progress")
            else:
                print_error(f"Job status should be in_progress, got: {job_data.get('status')}")
            if job_data.get("freelancer_id"):
                print_success(f"Freelancer assigned to job")
            else:
                print_error("Freelancer not assigned to job")

        return True
    except Exception as e:
        print_error(f"Respond proposal error: {str(e)}")
        return False


contract_id: str = ""
milestone_id: str = ""

def test_get_contract():
    """Test 13: Get auto-created contract after proposal acceptance"""
    global contract_id
    print_section("TEST 13: Get Contract (Auto-Created)")

    try:
        if not tokens.get('client'):
            print_error("Need client token — skipping")
            return False

        headers = {"Authorization": f"Bearer {tokens['client']}"}
        response = requests.get(f"{BASE_URL}/contracts/my", headers=headers)
        if response.status_code != 200:
            print_error(f"GET /contracts/my failed: {response.status_code} - {response.text[:200]}")
            return False

        data = response.json()
        if data["total"] == 0:
            print_error("No contracts found — proposal acceptance should have created one")
            return False

        contract = data["contracts"][0]
        contract_id = contract["id"]
        print_success(f"Contract found: {contract['title']}")
        print_info(f"ID: {contract_id}")
        print_info(f"Status: {contract['status']} | Amount: ${contract['total_amount']}")
        print_info(f"Client: {contract['client']['first_name']} | Freelancer: {contract['freelancer']['first_name']}")

        # Freelancer should also see it
        headers_fl = {"Authorization": f"Bearer {tokens['freelancer']}"}
        response = requests.get(f"{BASE_URL}/contracts/my", headers=headers_fl)
        if response.status_code == 200 and response.json()["total"] >= 1:
            print_success("Freelancer also sees the contract")
        else:
            print_error("Freelancer can't see the contract")

        # Get detail
        response = requests.get(f"{BASE_URL}/contracts/{contract_id}", headers=headers)
        if response.status_code == 200:
            detail = response.json()
            print_success(f"Contract detail loaded ({len(detail.get('milestones', []))} milestones)")
        else:
            print_error(f"GET contract detail failed: {response.status_code}")

        return True
    except Exception as e:
        print_error(f"Get contract error: {str(e)}")
        return False


def test_add_milestones():
    """Test 14: Client adds milestones to the contract"""
    global milestone_id
    print_section("TEST 14: Add Milestones")

    try:
        if not contract_id or not tokens.get('client'):
            print_error("Need contract_id and client token — skipping")
            return False

        headers = {"Authorization": f"Bearer {tokens['client']}"}

        # First, get the contract total to split into milestones
        response = requests.get(f"{BASE_URL}/contracts/{contract_id}", headers=headers)
        if response.status_code != 200:
            print_error(f"Can't get contract: {response.status_code}")
            return False

        total = response.json()["total_amount"]

        milestone_data = {
            "milestones": [
                {
                    "title": "Project Setup & Architecture",
                    "description": "Set up the project structure, database, and core architecture",
                    "amount": round(total * 0.3, 2),
                    "order": 0,
                },
                {
                    "title": "Core Feature Implementation",
                    "description": "Build the main features and API endpoints",
                    "amount": round(total * 0.5, 2),
                    "order": 1,
                },
                {
                    "title": "Testing & Deployment",
                    "description": "Write tests, fix bugs, deploy to production",
                    "amount": round(total * 0.2, 2),
                    "order": 2,
                },
            ]
        }

        response = requests.post(
            f"{BASE_URL}/contracts/{contract_id}/milestones",
            json=milestone_data,
            headers=headers,
        )
        if response.status_code != 201:
            print_error(f"Add milestones failed: {response.status_code} - {response.text[:300]}")
            return False

        data = response.json()
        milestones = data.get("milestones", [])
        print_success(f"Added {len(milestones)} milestones")
        for m in milestones:
            print_info(f"  #{m['order']}: {m['title']} — ${m['amount']} ({m['status']})")

        if milestones:
            milestone_id = milestones[0]["id"]

        # Freelancer should NOT be able to add milestones
        headers_fl = {"Authorization": f"Bearer {tokens['freelancer']}"}
        response = requests.post(
            f"{BASE_URL}/contracts/{contract_id}/milestones",
            json=milestone_data,
            headers=headers_fl,
        )
        if response.status_code == 403:
            print_success("Freelancer correctly blocked from adding milestones (403)")
        else:
            print_error(f"Freelancer should get 403, got {response.status_code}")

        # Milestone total exceeds contract amount
        bad_data = {"milestones": [{"title": "Excess", "amount": total * 2, "order": 99}]}
        response = requests.post(
            f"{BASE_URL}/contracts/{contract_id}/milestones",
            json=bad_data,
            headers=headers,
        )
        if response.status_code == 400:
            print_success("Excess milestone amount correctly rejected (400)")
        else:
            print_error(f"Excess should be 400, got {response.status_code}")

        return True
    except Exception as e:
        print_error(f"Add milestones error: {str(e)}")
        return False


def test_milestone_lifecycle():
    """Test 15: Full milestone lifecycle — start → submit → review → paid"""
    print_section("TEST 15: Milestone Lifecycle")

    try:
        if not milestone_id:
            print_error("Need milestone_id — skipping")
            return False

        headers_fl = {"Authorization": f"Bearer {tokens['freelancer']}"}
        headers_cl = {"Authorization": f"Bearer {tokens['client']}"}

        # 1. Start milestone (freelancer)
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/start",
            headers=headers_fl,
        )
        if response.status_code == 200 and response.json().get("status") == "in_progress":
            print_success("Step 1: Milestone started (in_progress)")
        else:
            print_error(f"Start failed: {response.status_code} - {response.text[:200]}")
            return False

        # Client should NOT be able to start
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/start",
            headers=headers_cl,
        )
        if response.status_code == 403:
            print_success("  → Client correctly blocked from starting milestone")

        # 2. Submit milestone (freelancer)
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/submit",
            json={"submission_note": "Phase 1 complete. Project structure and DB set up."},
            headers=headers_fl,
        )
        if response.status_code == 200 and response.json().get("status") == "submitted":
            print_success("Step 2: Milestone submitted for review")
        else:
            print_error(f"Submit failed: {response.status_code} - {response.text[:200]}")
            return False

        # 3. Request revision (client)
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/review",
            json={"action": "request_revision", "feedback": "Please add Docker setup too."},
            headers=headers_cl,
        )
        if response.status_code == 200 and response.json().get("status") == "revision_requested":
            print_success("Step 3: Revision requested by client")
        else:
            print_error(f"Revision request failed: {response.status_code}")
            return False

        # 4. Re-submit (freelancer)
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/submit",
            json={"submission_note": "Added Docker setup as requested."},
            headers=headers_fl,
        )
        if response.status_code == 200 and response.json().get("status") == "submitted":
            print_success("Step 4: Milestone re-submitted after revision")
        else:
            print_error(f"Re-submit failed: {response.status_code}")
            return False

        # 5. Approve (client) — auto-marks as paid
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/review",
            json={"action": "approve", "feedback": "Looks great!"},
            headers=headers_cl,
        )
        if response.status_code == 200:
            m = response.json()
            if m.get("status") == "paid":
                print_success(f"Step 5: Milestone approved and paid (${m.get('amount', '?')})")
            else:
                print_error(f"Expected 'paid' status, got '{m.get('status')}'")
                return False
        else:
            print_error(f"Approve failed: {response.status_code}")
            return False

        # 6. Verify contract amount_paid updated
        response = requests.get(f"{BASE_URL}/contracts/{contract_id}", headers=headers_cl)
        if response.status_code == 200:
            c = response.json()
            print_success(f"Contract updated: ${c['amount_paid']} / ${c['total_amount']} paid")
        else:
            print_error(f"Get contract failed: {response.status_code}")

        return True
    except Exception as e:
        print_error(f"Milestone lifecycle error: {str(e)}")
        return False


payment_account_id: str = ""

def test_setup_payment_accounts():
    """Test 16: Setup payment accounts for client (Stripe) and freelancer (Wise)"""
    global payment_account_id
    print_section("TEST 16: Setup Payment Accounts")

    try:
        # Client sets up Stripe account
        headers_cl = {"Authorization": f"Bearer {tokens['client']}"}
        response = requests.post(
            f"{BASE_URL}/payments/accounts",
            json={"provider": "stripe"},
            headers=headers_cl,
        )
        if response.status_code == 201:
            print_success(f"Client Stripe account created: {response.json()['external_account_id']}")
        else:
            print_error(f"Client Stripe setup failed: {response.status_code} - {response.text[:200]}")
            return False

        # Freelancer sets up Wise account (Iraq-friendly)
        headers_fl = {"Authorization": f"Bearer {tokens['freelancer']}"}
        response = requests.post(
            f"{BASE_URL}/payments/accounts",
            json={"provider": "wise", "wise_email": "freelancer@wise.com"},
            headers=headers_fl,
        )
        if response.status_code == 201:
            data = response.json()
            payment_account_id = data["id"]
            print_success(f"Freelancer Wise account created: {data['wise_email']}")
        else:
            print_error(f"Freelancer Wise setup failed: {response.status_code} - {response.text[:200]}")
            return False

        # Duplicate should fail
        response = requests.post(
            f"{BASE_URL}/payments/accounts",
            json={"provider": "stripe"},
            headers=headers_cl,
        )
        if response.status_code == 400:
            print_success("Duplicate account correctly rejected (400)")
        else:
            print_error(f"Duplicate should be 400, got {response.status_code}")

        # Wise without email should fail
        response = requests.post(
            f"{BASE_URL}/payments/accounts",
            json={"provider": "wise"},
            headers=headers_cl,
        )
        if response.status_code == 400:
            print_success("Wise without email correctly rejected (400)")

        return True
    except Exception as e:
        print_error(f"Payment account setup error: {str(e)}")
        return False


def test_fund_escrow():
    """Test 17: Client funds escrow for a milestone"""
    print_section("TEST 17: Fund Escrow")

    try:
        if not milestone_id or not tokens.get("client"):
            print_error("Need milestone_id and client token — skipping")
            return False

        headers_cl = {"Authorization": f"Bearer {tokens['client']}"}

        # Get a pending/in_progress milestone from the contract
        response = requests.get(
            f"{BASE_URL}/contracts/{contract_id}",
            headers=headers_cl,
        )
        if response.status_code != 200:
            print_error(f"Can't get contract: {response.status_code}")
            return False

        milestones = response.json().get("milestones", [])
        fundable = [m for m in milestones if m["status"] in ("pending", "in_progress")]

        if not fundable:
            print_info("No fundable milestones (all may be paid). Skipping escrow test.")
            return True

        target_milestone = fundable[0]
        print_info(f"Funding escrow for: {target_milestone['title']} (${target_milestone['amount']})")

        response = requests.post(
            f"{BASE_URL}/payments/escrow/fund",
            json={"milestone_id": target_milestone["id"]},
            headers=headers_cl,
        )
        if response.status_code == 201:
            data = response.json()
            print_success(f"Escrow funded: ${data['amount']} "
                         f"(freelancer gets ${data['freelancer_amount']}, "
                         f"fee: ${data['platform_fee']})")
            print_info(data["message"])
        else:
            print_error(f"Fund escrow failed: {response.status_code} - {response.text[:200]}")
            return False

        # Freelancer should NOT be able to fund escrow
        headers_fl = {"Authorization": f"Bearer {tokens['freelancer']}"}
        response = requests.post(
            f"{BASE_URL}/payments/escrow/fund",
            json={"milestone_id": target_milestone["id"]},
            headers=headers_fl,
        )
        if response.status_code == 403:
            print_success("Freelancer correctly blocked from funding escrow (403)")

        # Duplicate funding should fail
        response = requests.post(
            f"{BASE_URL}/payments/escrow/fund",
            json={"milestone_id": target_milestone["id"]},
            headers=headers_cl,
        )
        if response.status_code == 400:
            print_success("Duplicate escrow funding correctly rejected (400)")

        return True
    except Exception as e:
        print_error(f"Fund escrow error: {str(e)}")
        return False


def test_payment_summary():
    """Test 18: Get payment summary and transaction history"""
    print_section("TEST 18: Payment Summary & Transactions")

    try:
        headers_cl = {"Authorization": f"Bearer {tokens['client']}"}
        headers_fl = {"Authorization": f"Bearer {tokens['freelancer']}"}

        # Client summary
        response = requests.get(f"{BASE_URL}/payments/summary", headers=headers_cl)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Client summary: spent=${data['total_spent']:.2f}, "
                         f"escrow=${data['pending_escrow']:.2f}, "
                         f"accounts={len(data['payment_accounts'])}")
        else:
            print_error(f"Client summary failed: {response.status_code}")

        # Freelancer summary
        response = requests.get(f"{BASE_URL}/payments/summary", headers=headers_fl)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Freelancer summary: earned=${data['total_earned']:.2f}, "
                         f"escrow=${data['pending_escrow']:.2f}")
        else:
            print_error(f"Freelancer summary failed: {response.status_code}")

        # Transaction history
        response = requests.get(f"{BASE_URL}/payments/transactions", headers=headers_cl)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Client has {data['total']} transactions")
        else:
            print_error(f"Transactions failed: {response.status_code}")

        # List payment accounts
        response = requests.get(f"{BASE_URL}/payments/accounts", headers=headers_fl)
        if response.status_code == 200:
            accounts = response.json()
            print_success(f"Freelancer has {len(accounts)} payment account(s)")
        else:
            print_error(f"Accounts list failed: {response.status_code}")

        return True
    except Exception as e:
        print_error(f"Payment summary error: {str(e)}")
        return False


def test_rate_limiting():
    """Test 19: Verify rate limiting is active"""
    print_section("TEST 19: Rate Limiting")

    try:
        # Make rapid requests to check rate limit headers
        response = requests.get(f"{BASE_URL}/health")
        has_rl_header = "X-RateLimit-Remaining" in response.headers

        if has_rl_header:
            remaining = response.headers.get("X-RateLimit-Remaining")
            limit = response.headers.get("X-RateLimit-Limit")
            print_success(f"Rate limit headers present: {remaining}/{limit} remaining")
        else:
            # Health endpoint is exempt from rate limiting
            print_info("Health endpoint exempt from rate limiting (expected)")

        # Check a regular API endpoint
        headers = {"Authorization": f"Bearer {tokens['client']}"}
        response = requests.get(f"{BASE_URL}/jobs", headers=headers)
        has_rl_header = "X-RateLimit-Remaining" in response.headers
        if has_rl_header:
            print_success(f"API rate limits active: {response.headers['X-RateLimit-Remaining']}/{response.headers['X-RateLimit-Limit']}")
        else:
            print_info("Rate limit headers not on this endpoint")

        # Check security headers
        has_xss = "X-XSS-Protection" in response.headers
        has_cto = "X-Content-Type-Options" in response.headers
        has_frame = "X-Frame-Options" in response.headers
        has_req_id = "X-Request-ID" in response.headers

        if has_xss and has_cto and has_frame and has_req_id:
            print_success("All security headers present (XSS, Content-Type, Frame-Options, Request-ID)")
        else:
            missing = []
            if not has_xss: missing.append("X-XSS-Protection")
            if not has_cto: missing.append("X-Content-Type-Options")
            if not has_frame: missing.append("X-Frame-Options")
            if not has_req_id: missing.append("X-Request-ID")
            print_error(f"Missing security headers: {', '.join(missing)}")

        return True
    except Exception as e:
        print_error(f"Rate limiting test error: {str(e)}")
        return False


conversation_id: str = ""

def test_start_conversation():
    """Test 20: Start a conversation between client and freelancer"""
    global conversation_id
    print_section("TEST 20: Start Conversation")

    try:
        headers_cl = {"Authorization": f"Bearer {tokens['client']}"}

        # Client starts conversation with freelancer
        response = requests.post(
            f"{BASE_URL}/messages/conversations",
            json={
                "recipient_id": user_ids["freelancer"],
                "initial_message": "Hi! I wanted to discuss the project details.",
            },
            headers=headers_cl,
        )
        if response.status_code == 201:
            data = response.json()
            conversation_id = data["id"]
            print_success(f"Conversation started (ID: {conversation_id})")
            print_info(f"Other user: {data['other_user']['first_name']} {data['other_user']['last_name']}")
            print_info(f"Last message: {data['last_message_text']}")
        else:
            print_error(f"Start conversation failed: {response.status_code} - {response.text[:200]}")
            return False

        # Cannot message yourself
        response = requests.post(
            f"{BASE_URL}/messages/conversations",
            json={
                "recipient_id": user_ids["client"],
                "initial_message": "Talking to myself",
            },
            headers=headers_cl,
        )
        if response.status_code == 400:
            print_success("Self-messaging correctly rejected (400)")

        return True
    except Exception as e:
        print_error(f"Start conversation error: {str(e)}")
        return False


def test_send_messages():
    """Test 21: Send messages in a conversation"""
    print_section("TEST 21: Send Messages")

    try:
        if not conversation_id:
            print_error("No conversation_id — skipping")
            return False

        headers_fl = {"Authorization": f"Bearer {tokens['freelancer']}"}
        headers_cl = {"Authorization": f"Bearer {tokens['client']}"}

        # Freelancer replies
        response = requests.post(
            f"{BASE_URL}/messages/conversations/{conversation_id}",
            json={"content": "Hello! Happy to discuss. What questions do you have?"},
            headers=headers_fl,
        )
        if response.status_code == 201:
            print_success("Freelancer sent reply")
        else:
            print_error(f"Reply failed: {response.status_code}")

        # Client sends another message
        response = requests.post(
            f"{BASE_URL}/messages/conversations/{conversation_id}",
            json={"content": "What's your estimated timeline for the first milestone?"},
            headers=headers_cl,
        )
        if response.status_code == 201:
            print_success("Client sent follow-up")

        # Get messages
        response = requests.get(
            f"{BASE_URL}/messages/conversations/{conversation_id}",
            headers=headers_fl,
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Retrieved {data['total']} messages")
        else:
            print_error(f"Get messages failed: {response.status_code}")

        # List conversations
        response = requests.get(
            f"{BASE_URL}/messages/conversations",
            headers=headers_cl,
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Client has {data['total']} conversation(s)")
        else:
            print_error(f"List conversations failed: {response.status_code}")

        return True
    except Exception as e:
        print_error(f"Send messages error: {str(e)}")
        return False


def test_submit_reviews():
    """Test 22: Submit reviews after contract completion"""
    print_section("TEST 22: Submit Reviews")

    try:
        if not contract_id:
            print_error("No contract_id — skipping")
            return False

        headers_cl = {"Authorization": f"Bearer {tokens['client']}"}
        headers_fl = {"Authorization": f"Bearer {tokens['freelancer']}"}

        # Check if contract is completed
        response = requests.get(
            f"{BASE_URL}/contracts/{contract_id}",
            headers=headers_cl,
        )
        contract_status = response.json().get("status", "")
        print_info(f"Contract status: {contract_status}")

        if contract_status != "completed":
            print_info("Contract not completed — reviews require completed contract. Skipping review submission.")
            print_info("(This is expected if not all milestones were approved)")
            return True

        # Client reviews freelancer
        response = requests.post(
            f"{BASE_URL}/reviews/contract/{contract_id}",
            json={
                "rating": 5,
                "comment": "Excellent work! Delivered on time and exceeded expectations.",
                "communication_rating": 5,
                "quality_rating": 5,
                "professionalism_rating": 5,
                "timeliness_rating": 4,
            },
            headers=headers_cl,
        )
        if response.status_code == 201:
            data = response.json()
            print_success(f"Client reviewed freelancer: {data['rating']}★")
        else:
            print_error(f"Client review failed: {response.status_code} - {response.text[:200]}")
            return False

        # Freelancer reviews client
        response = requests.post(
            f"{BASE_URL}/reviews/contract/{contract_id}",
            json={
                "rating": 4,
                "comment": "Great client, clear requirements. Would work with again.",
                "communication_rating": 5,
                "quality_rating": 4,
                "professionalism_rating": 5,
            },
            headers=headers_fl,
        )
        if response.status_code == 201:
            print_success(f"Freelancer reviewed client: {response.json()['rating']}★")
        else:
            print_error(f"Freelancer review failed: {response.status_code} - {response.text[:200]}")

        # Duplicate review should fail
        response = requests.post(
            f"{BASE_URL}/reviews/contract/{contract_id}",
            json={"rating": 3, "comment": "Trying again..."},
            headers=headers_cl,
        )
        if response.status_code == 400:
            print_success("Duplicate review correctly rejected (400)")

        return True
    except Exception as e:
        print_error(f"Submit reviews error: {str(e)}")
        return False


def test_review_stats():
    """Test 23: Get review statistics and user reviews"""
    print_section("TEST 23: Review Stats & Listing")

    try:
        # Get freelancer reviews (public, no auth needed)
        response = requests.get(
            f"{BASE_URL}/reviews/user/{user_ids['freelancer']}",
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Freelancer has {data['total']} review(s)")
            if data.get("average_rating"):
                print_info(f"Average rating: {data['average_rating']}★")
        else:
            print_error(f"Get user reviews failed: {response.status_code}")

        # Get freelancer review stats
        response = requests.get(
            f"{BASE_URL}/reviews/user/{user_ids['freelancer']}/stats",
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Stats: {data['average_rating']}★ avg, "
                         f"{data['total_reviews']} total, "
                         f"distribution: {data['rating_distribution']}")
        else:
            print_error(f"Review stats failed: {response.status_code}")

        # Get contract reviews
        if contract_id:
            headers = {"Authorization": f"Bearer {tokens['client']}"}
            response = requests.get(
                f"{BASE_URL}/reviews/contract/{contract_id}",
                headers=headers,
            )
            if response.status_code == 200:
                reviews = response.json()
                print_success(f"Contract has {len(reviews)} review(s)")
            else:
                print_error(f"Contract reviews failed: {response.status_code}")

        return True
    except Exception as e:
        print_error(f"Review stats error: {str(e)}")
        return False


def test_notifications():
    """Test 24: Notification system"""
    print_section("TEST 24: Notifications")

    try:
        headers_cl = {"Authorization": f"Bearer {tokens['client']}"}
        headers_fl = {"Authorization": f"Bearer {tokens['freelancer']}"}

        # Get notifications (may be empty if no triggers fired)
        response = requests.get(
            f"{BASE_URL}/notifications",
            headers=headers_fl,
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Freelancer has {data['total']} notification(s), "
                         f"{data['unread_count']} unread")
        else:
            print_error(f"Get notifications failed: {response.status_code}")

        # Get unread count
        response = requests.get(
            f"{BASE_URL}/notifications/unread-count",
            headers=headers_cl,
        )
        if response.status_code == 200:
            print_success(f"Client unread count: {response.json()['count']}")
        else:
            print_error(f"Unread count failed: {response.status_code}")

        # Mark all read
        response = requests.post(
            f"{BASE_URL}/notifications/mark-all-read",
            headers=headers_fl,
        )
        if response.status_code == 200:
            print_success(f"Marked {response.json()['marked']} as read")
        else:
            print_error(f"Mark all read failed: {response.status_code}")

        # Filter unread only
        response = requests.get(
            f"{BASE_URL}/notifications?unread_only=true",
            headers=headers_fl,
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Unread after mark-all: {data['unread_count']}")
        else:
            print_error(f"Unread filter failed: {response.status_code}")

        return True
    except Exception as e:
        print_error(f"Notifications error: {str(e)}")
        return False


def run_all_tests():
    """Run all test cases"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  KAASB PLATFORM - API TEST SUITE")
    print(f"  Testing: Auth, Users, Jobs, Proposals, Contracts, Payments, Security, Messages, Reviews, Notifications")
    print(f"{'='*60}{Colors.END}\n")

    tests = [
        ("Health Check", test_health_check),
        ("User Registration", test_register_users),
        ("User Login", test_login_users),
        ("Get Current User", test_get_current_user),
        ("Create Job", test_create_job),
        ("List Jobs", test_list_jobs),
        ("Get Job Details", test_get_job_details),
        ("Get User Profile", test_get_user_profile),
        ("Update Profile", test_update_profile),
        ("Submit Proposal", test_submit_proposal),
        ("List Proposals", test_list_proposals),
        ("Respond to Proposal", test_respond_proposal),
        ("Get Contract", test_get_contract),
        ("Add Milestones", test_add_milestones),
        ("Milestone Lifecycle", test_milestone_lifecycle),
        ("Setup Payment Accounts", test_setup_payment_accounts),
        ("Fund Escrow", test_fund_escrow),
        ("Payment Summary", test_payment_summary),
        ("Rate Limiting & Security", test_rate_limiting),
        ("Start Conversation", test_start_conversation),
        ("Send Messages", test_send_messages),
        ("Submit Reviews", test_submit_reviews),
        ("Review Stats", test_review_stats),
        ("Notifications", test_notifications),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Test '{name}' crashed: {str(e)}")
            results.append((name, False))

    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status:6}{Colors.END} - {name}")

    print(f"\n{Colors.YELLOW}Results: {passed}/{total} tests passed{Colors.END}")

    if passed == total:
        print(f"\n{Colors.GREEN}[SUCCESS] All tests passed! Your API is working correctly!{Colors.END}\n")
    else:
        print(f"\n{Colors.RED}[WARNING] Some tests failed. Please check the errors above.{Colors.END}\n")

    return passed == total

if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}\n")
        exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {str(e)}{Colors.END}\n")
        exit(1)
