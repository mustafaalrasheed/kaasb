"""
Kaasb Platform - API Test Script (Steps 1-3)
Run with: python test_api.py

Prerequisites:
  - Backend running at http://localhost:8000
  - Database migrated (alembic upgrade head)
  - pip install requests
"""

import requests
import sys
import json
import os

BASE_URL = "http://localhost:8000/api/v1"

# Track results
passed = 0
failed = 0
errors = []


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        errors.append(f"{name}: {detail}")
        print(f"  ❌ {name} — {detail}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ============================================================
#  STEP 1: Health & Auth
# ============================================================

section("STEP 1: Health Check")

r = requests.get(f"{BASE_URL}/health")
test("GET /health returns 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
test("Health has db_status", "db_status" in data, f"keys: {list(data.keys())}")

# --- Registration ---
section("STEP 1: Registration")

# Register a CLIENT
client_data = {
    "email": "testclient@kaasb.com",
    "username": "testclient",
    "password": "TestPass1!",
    "first_name": "Ali",
    "last_name": "Hassan",
    "primary_role": "client",
}
r = requests.post(f"{BASE_URL}/auth/register", json=client_data)
test("Register client returns 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
if r.status_code == 201:
    client_tokens = r.json()
    test("Client gets access_token", "access_token" in client_tokens)
    test("Client gets refresh_token", "refresh_token" in client_tokens)
else:
    client_tokens = None

# Register a FREELANCER
freelancer_data = {
    "email": "testfreelancer@kaasb.com",
    "username": "testfreelancer",
    "password": "TestPass1!",
    "first_name": "Sara",
    "last_name": "Ahmed",
    "primary_role": "freelancer",
}
r = requests.post(f"{BASE_URL}/auth/register", json=freelancer_data)
test("Register freelancer returns 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
if r.status_code == 201:
    freelancer_tokens = r.json()
else:
    freelancer_tokens = None

# Duplicate email
r = requests.post(f"{BASE_URL}/auth/register", json=client_data)
test("Duplicate email returns 409", r.status_code == 409, f"got {r.status_code}")

# Weak password
weak = {**client_data, "email": "weak@kaasb.com", "username": "weakuser", "password": "short"}
r = requests.post(f"{BASE_URL}/auth/register", json=weak)
test("Weak password rejected (422)", r.status_code == 422, f"got {r.status_code}")

# --- Login ---
section("STEP 1: Login")

r = requests.post(f"{BASE_URL}/auth/login", json={"email": "testclient@kaasb.com", "password": "TestPass1!"})
test("Login returns 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    client_tokens = r.json()  # Use fresh tokens
    test("Login returns access_token", "access_token" in client_tokens)

r = requests.post(f"{BASE_URL}/auth/login", json={"email": "testclient@kaasb.com", "password": "WrongPass1!"})
test("Wrong password returns 401", r.status_code == 401, f"got {r.status_code}")

r = requests.post(f"{BASE_URL}/auth/login", json={"email": "nobody@kaasb.com", "password": "TestPass1!"})
test("Unknown email returns 401", r.status_code == 401, f"got {r.status_code}")

# --- Get Me ---
section("STEP 1: Get Current User")

if client_tokens:
    headers_client = {"Authorization": f"Bearer {client_tokens['access_token']}"}
    r = requests.get(f"{BASE_URL}/auth/me", headers=headers_client)
    test("GET /auth/me returns 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        me = r.json()
        test("Me has correct email", me.get("email") == "testclient@kaasb.com", f"got {me.get('email')}")
        test("Me has correct role", me.get("primary_role") == "client", f"got {me.get('primary_role')}")
        test("Me has id", "id" in me)
        test("Me has created_at", "created_at" in me)

# Bad token
r = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": "Bearer invalid_token"})
test("Bad token returns 401", r.status_code == 401, f"got {r.status_code}")

# No token
r = requests.get(f"{BASE_URL}/auth/me")
test("No token returns 401", r.status_code == 401, f"got {r.status_code}")

# --- Refresh Token ---
section("STEP 1: Token Refresh")

if client_tokens:
    r = requests.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": client_tokens["refresh_token"]})
    test("Refresh returns 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        new_tokens = r.json()
        test("Refresh returns new access_token", "access_token" in new_tokens)
        # Update tokens
        client_tokens = new_tokens
        headers_client = {"Authorization": f"Bearer {client_tokens['access_token']}"}


# ============================================================
#  STEP 2: User Profiles
# ============================================================

section("STEP 2: Profile Update (Client)")

if client_tokens:
    update_data = {
        "display_name": "Ali H.",
        "bio": "I am a tech entrepreneur looking for talented developers.",
        "country": "Iraq",
        "city": "Baghdad",
        "timezone": "Asia/Baghdad",
        "phone": "+964 770 123 4567",
    }
    r = requests.put(f"{BASE_URL}/users/profile", json=update_data, headers=headers_client)
    test("Update client profile returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        updated = r.json()
        test("Display name updated", updated.get("display_name") == "Ali H.")
        test("Bio updated", updated.get("bio") == update_data["bio"])
        test("Country updated", updated.get("country") == "Iraq")
        test("Timezone returned", updated.get("timezone") == "Asia/Baghdad")
        test("Phone returned", updated.get("phone") == "+964 770 123 4567")

    # Client should NOT be able to set freelancer fields
    r = requests.put(f"{BASE_URL}/users/profile", json={"title": "Developer"}, headers=headers_client)
    test("Client can't set freelancer fields", r.status_code == 400, f"got {r.status_code}")

section("STEP 2: Profile Update (Freelancer)")

if freelancer_tokens:
    headers_freelancer = {"Authorization": f"Bearer {freelancer_tokens['access_token']}"}

    # Re-login freelancer to get fresh tokens
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "testfreelancer@kaasb.com", "password": "TestPass1!"})
    if r.status_code == 200:
        freelancer_tokens = r.json()
        headers_freelancer = {"Authorization": f"Bearer {freelancer_tokens['access_token']}"}

    update_data = {
        "display_name": "Sara A.",
        "bio": "Experienced full-stack developer with 5 years of Python and React expertise.",
        "country": "Iraq",
        "city": "Erbil",
        "title": "Senior Python Developer",
        "hourly_rate": 35.0,
        "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
        "experience_level": "expert",
        "portfolio_url": "https://sara-portfolio.dev",
    }
    r = requests.put(f"{BASE_URL}/users/profile", json=update_data, headers=headers_freelancer)
    test("Update freelancer profile returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        updated = r.json()
        test("Title updated", updated.get("title") == "Senior Python Developer")
        test("Hourly rate updated", updated.get("hourly_rate") == 35.0)
        test("Skills updated", updated.get("skills") == ["Python", "FastAPI", "React", "PostgreSQL", "Docker"])
        test("Experience level updated", updated.get("experience_level") == "expert")

section("STEP 2: Public Profile")

r = requests.get(f"{BASE_URL}/users/profile/testfreelancer")
test("Get public profile returns 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    profile = r.json()
    test("Public profile has username", profile.get("username") == "testfreelancer")
    test("Public profile has skills", len(profile.get("skills", [])) == 5)
    test("Public profile NO email", "email" not in profile)
    test("Public profile NO phone", "phone" not in profile)

r = requests.get(f"{BASE_URL}/users/profile/nonexistentuser")
test("Unknown username returns 404", r.status_code == 404, f"got {r.status_code}")

section("STEP 2: Search Freelancers")

r = requests.get(f"{BASE_URL}/users/freelancers")
test("Browse freelancers returns 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    data = r.json()
    test("Response has 'users' list", isinstance(data.get("users"), list))
    test("Response has 'total'", "total" in data)
    test("Response has pagination", "page" in data and "total_pages" in data)
    test("Found at least 1 freelancer", data.get("total", 0) >= 1, f"total={data.get('total')}")

# Search with skills filter
r = requests.get(f"{BASE_URL}/users/freelancers", params={"skills": "Python"})
test("Filter by skill returns results", r.status_code == 200 and r.json().get("total", 0) >= 1,
     f"status={r.status_code}, total={r.json().get('total', 0) if r.status_code == 200 else 'N/A'}")

# Search with text query
r = requests.get(f"{BASE_URL}/users/freelancers", params={"q": "Sara"})
test("Search by name works", r.status_code == 200 and r.json().get("total", 0) >= 1)

# Search with no match
r = requests.get(f"{BASE_URL}/users/freelancers", params={"q": "zzzznonexistent"})
test("No match returns empty", r.status_code == 200 and r.json().get("total") == 0)

section("STEP 2: Password Change")

if client_tokens:
    r = requests.put(
        f"{BASE_URL}/users/password",
        json={"current_password": "TestPass1!", "new_password": "NewPass2@"},
        headers=headers_client,
    )
    test("Change password returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

    # Login with new password
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "testclient@kaasb.com", "password": "NewPass2@"})
    test("Login with new password works", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        client_tokens = r.json()
        headers_client = {"Authorization": f"Bearer {client_tokens['access_token']}"}

    # Old password should fail
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "testclient@kaasb.com", "password": "TestPass1!"})
    test("Old password rejected", r.status_code == 401, f"got {r.status_code}")


# ============================================================
#  STEP 3: Job Posting & Listing
# ============================================================

section("STEP 3: Create Job (Client)")

job_data = {
    "title": "Build a FastAPI REST API for E-commerce Platform",
    "description": "We need an experienced Python developer to build a complete REST API using FastAPI. " * 5,
    "category": "Web Development",
    "job_type": "fixed",
    "fixed_price": 1500.0,
    "skills_required": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "experience_level": "intermediate",
    "duration": "1_to_4_weeks",
}

job_id = None
if client_tokens:
    r = requests.post(f"{BASE_URL}/jobs", json=job_data, headers=headers_client)
    test("Create job returns 201", r.status_code == 201, f"got {r.status_code}: {r.text[:300]}")
    if r.status_code == 201:
        job = r.json()
        job_id = job["id"]
        test("Job has correct title", job.get("title") == job_data["title"])
        test("Job has client info", "client" in job and "username" in job.get("client", {}))
        test("Job status is 'open'", job.get("status") == "open")
        test("Job has skills", job.get("skills_required") == job_data["skills_required"])
        test("Job has fixed_price", job.get("fixed_price") == 1500.0)
        test("Job has published_at", job.get("published_at") is not None)

# Create a second job (hourly)
hourly_job_id = None
if client_tokens:
    hourly_data = {
        "title": "Ongoing React Frontend Development for SaaS Dashboard",
        "description": "Looking for a React developer to help build and maintain our SaaS dashboard. " * 5,
        "category": "Web Development",
        "job_type": "hourly",
        "budget_min": 25.0,
        "budget_max": 50.0,
        "skills_required": ["React", "TypeScript", "Tailwind CSS"],
        "experience_level": "expert",
        "duration": "3_to_6_months",
    }
    r = requests.post(f"{BASE_URL}/jobs", json=hourly_data, headers=headers_client)
    test("Create hourly job returns 201", r.status_code == 201, f"got {r.status_code}: {r.text[:300]}")
    if r.status_code == 201:
        hourly_job_id = r.json()["id"]

section("STEP 3: Create Job (Validation)")

# Freelancer should NOT be able to post jobs
if freelancer_tokens:
    r = requests.post(f"{BASE_URL}/jobs", json=job_data, headers=headers_freelancer)
    test("Freelancer can't post jobs (403)", r.status_code == 403, f"got {r.status_code}")

# Missing required fields
if client_tokens:
    r = requests.post(f"{BASE_URL}/jobs", json={"title": "Short"}, headers=headers_client)
    test("Incomplete job rejected (422)", r.status_code == 422, f"got {r.status_code}")

# Fixed job without fixed_price
if client_tokens:
    bad_job = {**job_data, "fixed_price": None}
    del bad_job["fixed_price"]
    r = requests.post(f"{BASE_URL}/jobs", json=bad_job, headers=headers_client)
    test("Fixed job without price rejected", r.status_code == 422, f"got {r.status_code}")

section("STEP 3: Get Job Details")

if job_id:
    r = requests.get(f"{BASE_URL}/jobs/{job_id}")
    test("Get job returns 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        job = r.json()
        test("Job has full description", len(job.get("description", "")) > 50)
        test("Job has client.username", job.get("client", {}).get("username") == "testclient")
        test("View count incremented", job.get("view_count", 0) >= 1, f"views={job.get('view_count')}")

# Non-existent job
r = requests.get(f"{BASE_URL}/jobs/00000000-0000-0000-0000-000000000000")
test("Non-existent job returns 404", r.status_code == 404, f"got {r.status_code}")

section("STEP 3: Browse & Search Jobs")

r = requests.get(f"{BASE_URL}/jobs")
test("Browse jobs returns 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    data = r.json()
    test("Response has 'jobs' list", isinstance(data.get("jobs"), list))
    test("Found at least 2 jobs", data.get("total", 0) >= 2, f"total={data.get('total')}")
    test("Jobs have client info", all("client" in j for j in data.get("jobs", [])))

# Search by keyword
r = requests.get(f"{BASE_URL}/jobs", params={"q": "FastAPI"})
test("Search by keyword works", r.status_code == 200 and r.json().get("total", 0) >= 1)

# Filter by category
r = requests.get(f"{BASE_URL}/jobs", params={"category": "Web Development"})
test("Filter by category works", r.status_code == 200 and r.json().get("total", 0) >= 1)

# Filter by job type
r = requests.get(f"{BASE_URL}/jobs", params={"job_type": "hourly"})
test("Filter by hourly works", r.status_code == 200 and r.json().get("total", 0) >= 1)

# Filter by skills
r = requests.get(f"{BASE_URL}/jobs", params={"skills": "Python"})
test("Filter by skill works", r.status_code == 200 and r.json().get("total", 0) >= 1)

# Sort by budget
r = requests.get(f"{BASE_URL}/jobs", params={"sort_by": "budget_high"})
test("Sort by budget_high works", r.status_code == 200)

section("STEP 3: My Posted Jobs")

if client_tokens:
    r = requests.get(f"{BASE_URL}/jobs/my/posted", headers=headers_client)
    test("GET /jobs/my/posted returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        data = r.json()
        test("Client sees their jobs", data.get("total", 0) >= 2, f"total={data.get('total')}")

    # Filter by status
    r = requests.get(f"{BASE_URL}/jobs/my/posted", params={"status": "open"}, headers=headers_client)
    test("Filter my jobs by status works", r.status_code == 200)

section("STEP 3: Update Job")

if job_id and client_tokens:
    r = requests.put(
        f"{BASE_URL}/jobs/{job_id}",
        json={"title": "Updated: Build a FastAPI REST API for E-commerce"},
        headers=headers_client,
    )
    test("Update job returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        test("Title was updated", "Updated:" in r.json().get("title", ""))

# Freelancer can't update client's job
if job_id and freelancer_tokens:
    r = requests.put(
        f"{BASE_URL}/jobs/{job_id}",
        json={"title": "Hacked title"},
        headers=headers_freelancer,
    )
    test("Freelancer can't update job (403)", r.status_code == 403, f"got {r.status_code}")

section("STEP 3: Close Job")

if hourly_job_id and client_tokens:
    r = requests.post(f"{BASE_URL}/jobs/{hourly_job_id}/close", headers=headers_client)
    test("Close job returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        test("Job status is 'closed'", r.json().get("status") == "closed")

    # Can't close again
    r = requests.post(f"{BASE_URL}/jobs/{hourly_job_id}/close", headers=headers_client)
    test("Can't close already closed job (400)", r.status_code == 400, f"got {r.status_code}")

section("STEP 3: Delete Job")

if job_id and client_tokens:
    r = requests.delete(f"{BASE_URL}/jobs/{job_id}", headers=headers_client)
    test("Delete job returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

    # Verify it's gone
    r = requests.get(f"{BASE_URL}/jobs/{job_id}")
    test("Deleted job returns 404", r.status_code == 404, f"got {r.status_code}")


# ============================================================
#  RESULTS
# ============================================================

print(f"\n{'='*60}")
print(f"  RESULTS")
print(f"{'='*60}")
print(f"  ✅ Passed: {passed}")
print(f"  ❌ Failed: {failed}")
print(f"  Total:    {passed + failed}")

if errors:
    print(f"\n  Failed tests:")
    for e in errors:
        print(f"    • {e}")

print()
sys.exit(0 if failed == 0 else 1)
