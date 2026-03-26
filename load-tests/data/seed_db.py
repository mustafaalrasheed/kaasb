"""
Kaasb Load Test — Database Seeder
===================================
Pre-populates the test/staging database with realistic Iraqi market data
so load tests start with a non-empty database (more realistic).

What this creates:
  - 50 client users
  - 100 freelancer users
  - 200 open job postings (realistic spread of categories/budgets)
  - 500 proposals across the jobs

Usage:
  # Point at your staging API:
  python seed_db.py --host http://staging.kaasb.com --clients 50 --freelancers 100 --jobs 200

  # Local development:
  python seed_db.py --host http://localhost:8000

  # Dry run (print what would be created):
  python seed_db.py --dry-run

Requirements:
  pip install httpx tqdm
"""

import argparse
import asyncio
import sys
import os
import json
import random
from datetime import datetime

import httpx

sys.path.insert(0, os.path.dirname(__file__))
from generator import IraqiDataGenerator

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    class tqdm:  # noqa: N801
        def __init__(self, total=None, desc=None, **kwargs):
            self.total = total
            self.desc = desc
            self.n = 0
        def update(self, n=1):
            self.n += n
            if self.total:
                pct = int(self.n / self.total * 100)
                print(f"\r{self.desc}: {self.n}/{self.total} ({pct}%)", end="", flush=True)
        def __enter__(self): return self
        def __exit__(self, *args):
            print()  # newline at end


class KaasbSeeder:
    def __init__(self, host: str, dry_run: bool = False):
        self.host    = host.rstrip("/")
        self.api     = f"{self.host}/api/v1"
        self.dry_run = dry_run
        self.gen     = IraqiDataGenerator(seed=42)
        self.client  = httpx.Client(timeout=30.0, follow_redirects=True)

        # Track created resources
        self.clients     : list[dict] = []
        self.freelancers : list[dict] = []
        self.jobs        : list[dict] = []
        self.proposals   : list[dict] = []
        self.errors      : list[str]  = []

    def _register(self, role: str, index: int) -> dict | None:
        data = self.gen.user(role=role, index=index)
        if self.dry_run:
            return {"email": data["email"], "token": "dry-run-token", "role": role}

        resp = self.client.post(
            f"{self.api}/auth/register",
            json={
                "email":        data["email"],
                "username":     data["username"],
                "password":     data["password"],
                "first_name":   data["first_name"],
                "last_name":    data["last_name"],
                "primary_role": role,
            },
        )
        if resp.status_code in (200, 201):
            token = resp.json().get("access_token")
            return {"email": data["email"], "token": token, "role": role, "data": data}
        else:
            self.errors.append(f"Register failed [{role} {index}]: {resp.status_code} — {resp.text[:100]}")
            return None

    def _post_job(self, client_token: str) -> dict | None:
        job_data = self.gen.job()
        if self.dry_run:
            return {"id": f"dry-run-job-{random.randint(1,9999)}", **job_data}

        resp = self.client.post(
            f"{self.api}/jobs",
            json=job_data,
            headers={"Authorization": f"Bearer {client_token}"},
        )
        if resp.status_code == 201:
            return resp.json()
        else:
            self.errors.append(f"Post job failed: {resp.status_code} — {resp.text[:100]}")
            return None

    def _submit_proposal(self, freelancer_token: str, job: dict) -> dict | None:
        proposal_data = self.gen.proposal(job)
        if self.dry_run:
            return {"id": f"dry-run-proposal-{random.randint(1,9999)}"}

        resp = self.client.post(
            f"{self.api}/proposals/jobs/{job['id']}",
            json=proposal_data,
            headers={"Authorization": f"Bearer {freelancer_token}"},
        )
        if resp.status_code == 201:
            return resp.json()
        elif resp.status_code == 409:
            return None  # Duplicate — expected, skip silently
        else:
            self.errors.append(f"Submit proposal failed: {resp.status_code}")
            return None

    # ── Main seeding flows ────────────────────────────────────────────────────

    def seed_users(self, n_clients: int, n_freelancers: int):
        print(f"\n{'DRY RUN — ' if self.dry_run else ''}Seeding {n_clients} clients + {n_freelancers} freelancers...")

        with tqdm(total=n_clients, desc="Clients") as bar:
            for i in range(n_clients):
                user = self._register("client", i)
                if user:
                    self.clients.append(user)
                bar.update(1)

        with tqdm(total=n_freelancers, desc="Freelancers") as bar:
            for i in range(n_freelancers):
                user = self._register("freelancer", i + 10_000)
                if user:
                    self.freelancers.append(user)
                bar.update(1)

        print(f"  Created: {len(self.clients)} clients, {len(self.freelancers)} freelancers")

    def seed_jobs(self, n_jobs: int):
        if not self.clients:
            print("ERROR: No clients registered. Run seed_users first.")
            return

        print(f"\nSeeding {n_jobs} jobs...")
        with tqdm(total=n_jobs, desc="Jobs") as bar:
            for i in range(n_jobs):
                client = random.choice(self.clients)
                job = self._post_job(client["token"])
                if job:
                    self.jobs.append(job)
                bar.update(1)

        print(f"  Created: {len(self.jobs)} jobs")

    def seed_proposals(self, proposals_per_job: int = 3):
        if not self.jobs or not self.freelancers:
            print("ERROR: Need jobs and freelancers first.")
            return

        total = min(len(self.jobs) * proposals_per_job, 1000)
        print(f"\nSeeding ~{total} proposals ({proposals_per_job} per job)...")

        created = 0
        with tqdm(total=total, desc="Proposals") as bar:
            for job in self.jobs[:len(self.jobs)]:
                # Each job gets 1–5 proposals from random freelancers
                count = random.randint(1, proposals_per_job)
                sample = random.sample(self.freelancers, min(count, len(self.freelancers)))
                for freelancer in sample:
                    prop = self._submit_proposal(freelancer["token"], job)
                    if prop:
                        self.proposals.append(prop)
                        created += 1
                    bar.update(1)

        print(f"  Created: {len(self.proposals)} proposals")

    def run(self, n_clients: int, n_freelancers: int, n_jobs: int):
        start = datetime.now()
        print("=" * 60)
        print(f"  Kaasb Database Seeder")
        print(f"  Target: {self.host}")
        print(f"  Mode:   {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("=" * 60)

        # Check server is reachable
        try:
            resp = self.client.get(f"{self.api}/health", timeout=5)
            print(f"  Server health: {resp.status_code}")
            if resp.status_code != 200:
                print("  WARNING: Server not healthy — seeding may fail")
        except Exception as e:
            print(f"  ERROR: Cannot reach server: {e}")
            if not self.dry_run:
                sys.exit(1)

        self.seed_users(n_clients, n_freelancers)
        self.seed_jobs(n_jobs)
        self.seed_proposals(proposals_per_job=3)

        elapsed = (datetime.now() - start).total_seconds()

        print("\n" + "=" * 60)
        print("  Seeding Complete")
        print("=" * 60)
        print(f"  Clients:     {len(self.clients):>6,}")
        print(f"  Freelancers: {len(self.freelancers):>6,}")
        print(f"  Jobs:        {len(self.jobs):>6,}")
        print(f"  Proposals:   {len(self.proposals):>6,}")
        print(f"  Errors:      {len(self.errors):>6,}")
        print(f"  Elapsed:     {elapsed:.1f}s")

        if self.errors:
            print(f"\n  First 5 errors:")
            for err in self.errors[:5]:
                print(f"    - {err}")

        # Save seed data for load tests to use as pre-existing accounts
        if not self.dry_run:
            seed_file = os.path.join(os.path.dirname(__file__), "seeded_users.json")
            with open(seed_file, "w") as f:
                json.dump({
                    "clients":     [{"email": u["email"], "token": u["token"]} for u in self.clients[:20]],
                    "freelancers": [{"email": u["email"], "token": u["token"]} for u in self.freelancers[:20]],
                    "job_ids":     [j["id"] for j in self.jobs[:50]],
                    "seeded_at":   datetime.now().isoformat(),
                }, f, indent=2)
            print(f"\n  Seed data saved to: {seed_file}")
            print("  (Load tests can use seeded_users.json to skip registration)")

        print("=" * 60)

    def close(self):
        self.client.close()


def main():
    parser = argparse.ArgumentParser(description="Kaasb database seeder for load testing")
    parser.add_argument("--host",        default="http://localhost:8000", help="API base URL")
    parser.add_argument("--clients",     type=int, default=50,  help="Number of client users to create")
    parser.add_argument("--freelancers", type=int, default=100, help="Number of freelancer users to create")
    parser.add_argument("--jobs",        type=int, default=200, help="Number of job postings to create")
    parser.add_argument("--dry-run",     action="store_true",   help="Simulate without making requests")
    args = parser.parse_args()

    seeder = KaasbSeeder(host=args.host, dry_run=args.dry_run)
    try:
        seeder.run(
            n_clients=args.clients,
            n_freelancers=args.freelancers,
            n_jobs=args.jobs,
        )
    finally:
        seeder.close()


if __name__ == "__main__":
    main()
