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

def test_contract_created():
    """Test 13: Verify contract was auto-created on proposal acceptance"""
    global contract_id
    print_section("TEST 13: Contract Auto-Creation")

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
        if data['total'] < 1:
            print_error(f"Expected at least 1 contract, got {data['total']}. Did the proposal get accepted in a previous test?")
            return False

        contract = data['contracts'][0]
        contract_id = contract['id']
        print_success(f"Contract found: {contract['title']} (ID: {contract_id})")
        print_info(f"Status: {contract['status']} | Amount: ${contract['total_amount']}")
        print_info(f"Milestones: {contract['completed_milestones']}/{contract['milestone_count']}")

        # Freelancer should also see the contract
        fl_headers = {"Authorization": f"Bearer {tokens['freelancer']}"}
        fl_response = requests.get(f"{BASE_URL}/contracts/my", headers=fl_headers)
        if fl_response.status_code == 200 and fl_response.json()['total'] >= 1:
            print_success("Freelancer also sees the contract")
        else:
            print_error("Freelancer doesn't see the contract")

        return True
    except Exception as e:
        print_error(f"Contract test error: {str(e)}")
        return False


def test_add_milestones():
    """Test 14: Client adds milestones to contract"""
    global milestone_id
    print_section("TEST 14: Add Milestones")

    try:
        if not contract_id or not tokens.get('client'):
            print_error("Need contract_id and client token — skipping")
            return False

        headers = {"Authorization": f"Bearer {tokens['client']}"}
        milestone_data = {
            "milestones": [
                {
                    "title": "Backend API Development",
                    "description": "Build all REST API endpoints",
                    "amount": 500.0,
                    "order": 0
                },
                {
                    "title": "Frontend Implementation",
                    "description": "Build React frontend pages",
                    "amount": 400.0,
                    "order": 1
                },
                {
                    "title": "Testing & Deployment",
                    "description": "QA testing and production deploy",
                    "amount": 300.0,
                    "order": 2
                }
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
        milestones = data.get('milestones', [])
        print_success(f"Added {len(milestones)} milestones")

        if len(milestones) >= 1:
            milestone_id = milestones[0]['id']
            for m in milestones:
                print_info(f"  #{m['order']+1} {m['title']} - ${m['amount']} ({m['status']})")

        # Freelancer can't add milestones
        fl_headers = {"Authorization": f"Bearer {tokens['freelancer']}"}
        fl_response = requests.post(
            f"{BASE_URL}/contracts/{contract_id}/milestones",
            json=milestone_data,
            headers=fl_headers,
        )
        if fl_response.status_code == 403:
            print_success("Freelancer correctly blocked from adding milestones (403)")
        else:
            print_error(f"Freelancer should get 403, got {fl_response.status_code}")

        return True
    except Exception as e:
        print_error(f"Add milestones error: {str(e)}")
        return False


def test_milestone_workflow():
    """Test 15: Full milestone lifecycle (start → submit → approve)"""
    print_section("TEST 15: Milestone Workflow")

    try:
        if not milestone_id or not tokens.get('freelancer') or not tokens.get('client'):
            print_error("Need milestone_id and both tokens — skipping")
            return False

        fl_headers = {"Authorization": f"Bearer {tokens['freelancer']}"}
        cl_headers = {"Authorization": f"Bearer {tokens['client']}"}

        # 1. Freelancer starts milestone
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/start",
            headers=fl_headers,
        )
        if response.status_code == 200 and response.json().get('status') == 'in_progress':
            print_success("Step 1: Freelancer started milestone → in_progress")
        else:
            print_error(f"Start failed: {response.status_code} - {response.text[:200]}")
            return False

        # 2. Freelancer submits milestone
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/submit",
            json={"submission_note": "Backend API complete with all endpoints and tests."},
            headers=fl_headers,
        )
        if response.status_code == 200 and response.json().get('status') == 'submitted':
            print_success("Step 2: Freelancer submitted milestone → submitted")
        else:
            print_error(f"Submit failed: {response.status_code} - {response.text[:200]}")
            return False

        # 3. Client requests revision
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/review",
            json={"action": "request_revision", "feedback": "Please add more error handling."},
            headers=cl_headers,
        )
        if response.status_code == 200 and response.json().get('status') == 'revision_requested':
            print_success("Step 3: Client requested revision → revision_requested")
        else:
            print_error(f"Revision request failed: {response.status_code} - {response.text[:200]}")
            return False

        # 4. Freelancer re-submits
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/submit",
            json={"submission_note": "Added comprehensive error handling."},
            headers=fl_headers,
        )
        if response.status_code == 200 and response.json().get('status') == 'submitted':
            print_success("Step 4: Freelancer re-submitted → submitted")
        else:
            print_error(f"Re-submit failed: {response.status_code} - {response.text[:200]}")
            return False

        # 5. Client approves
        response = requests.post(
            f"{BASE_URL}/contracts/milestones/{milestone_id}/review",
            json={"action": "approve", "feedback": "Looks great!"},
            headers=cl_headers,
        )
        if response.status_code == 200 and response.json().get('status') == 'paid':
            print_success("Step 5: Client approved → paid")
        else:
            print_error(f"Approve failed: {response.status_code} - {response.text[:200]}")
            return False

        # 6. Verify contract shows updated payment
        if contract_id:
            response = requests.get(f"{BASE_URL}/contracts/{contract_id}", headers=cl_headers)
            if response.status_code == 200:
                c = response.json()
                print_info(f"Contract: ${c['amount_paid']} / ${c['total_amount']} paid")
                print_info(f"Contract status: {c['status']}")

        return True
    except Exception as e:
        print_error(f"Milestone workflow error: {str(e)}")
        return False


def run_all_tests():
    """Run all test cases"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  KAASB PLATFORM - API TEST SUITE")
    print(f"  Testing: Auth, Users, Jobs, Proposals, Contracts")
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
        ("Contract Auto-Created", test_contract_created),
        ("Add Milestones", test_add_milestones),
        ("Milestone Workflow", test_milestone_workflow),
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
