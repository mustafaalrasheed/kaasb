/**
 * Kaasb — k6 Baseline Load Test
 * ================================
 * Normal expected daily load for 30 minutes.
 * Target: 50 concurrent users, Iraqi peak-hour simulation.
 *
 * Pass criteria:
 *   - Error rate < 1%
 *   - p95 response time < 2000ms
 *   - p99 response time < 5000ms
 *   - Availability > 99%
 *
 * Run:
 *   k6 run --env BASE_URL=https://kaasb.com baseline.js
 *   k6 run --env BASE_URL=http://localhost:8000 baseline.js  (local)
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";
import { randomItem, randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

// ── Config ─────────────────────────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API      = `${BASE_URL}/api/v1`;

// ── Custom metrics ─────────────────────────────────────────────────────────
const authErrors    = new Rate("auth_errors");
const searchLatency = new Trend("search_latency", true);
const jobViewLatency = new Trend("job_view_latency", true);
const apiErrors     = new Counter("api_errors");

// ── Load profile ────────────────────────────────────────────────────────────
export const options = {
  scenarios: {
    // Anonymous browsing (60%)
    browse: {
      executor:    "ramping-vus",
      startVUs:    0,
      stages: [
        { duration: "2m",  target: 30 },  // ramp up
        { duration: "25m", target: 30 },  // hold
        { duration: "3m",  target: 0  },  // ramp down
      ],
      exec: "browseScenario",
    },
    // Authenticated users (40%)
    authenticated: {
      executor:    "ramping-vus",
      startVUs:    0,
      stages: [
        { duration: "3m",  target: 20 },
        { duration: "24m", target: 20 },
        { duration: "3m",  target: 0  },
      ],
      exec: "authScenario",
    },
  },

  thresholds: {
    http_req_failed:                  ["rate<0.01"],       // < 1% errors
    http_req_duration:                ["p(95)<2000", "p(99)<5000"],
    "http_req_duration{name:search}": ["p(95)<1500"],      // search must be fast
    auth_errors:                      ["rate<0.02"],
  },
};

// ── Test data ──────────────────────────────────────────────────────────────
const SEARCH_TERMS = [
  "Python developer", "React", "mobile app", "UI design",
  "مطور", "تصميم", "ترجمة عربي", "WordPress",
];
const CATEGORIES = [
  "Web Development", "Mobile Development", "UI/UX Design",
  "Graphic Design", "Content Writing", "Translation",
];
const SKILLS = ["Python", "JavaScript", "React", "Flutter", "Figma", "Node.js"];
let _registeredUsers = [];

function makeEmail(prefix) {
  return `k6_${prefix}_${Date.now()}_${randomIntBetween(1000, 9999)}@loadtest.kaasb.com`;
}

function register(role) {
  const n = randomIntBetween(1000, 99999);
  const email = makeEmail(`${role}_${n}`);
  const payload = JSON.stringify({
    email,
    username:     `testuser${n}`,
    password:     "TestPass123!@#",
    first_name:   "Test",
    last_name:    "User",
    primary_role: role,
  });

  const resp = http.post(`${API}/auth/register`, payload, {
    headers: { "Content-Type": "application/json" },
    tags:    { name: "register" },
  });

  check(resp, { "register 2xx": (r) => r.status >= 200 && r.status < 300 });
  authErrors.add(resp.status >= 400);

  if (resp.status >= 200 && resp.status < 300) {
    const body = resp.json();
    return { token: body.access_token, email };
  }
  return null;
}

// ── Scenario: anonymous browsing ───────────────────────────────────────────
export function browseScenario() {
  group("Browse Jobs", () => {
    const params = {
      page:      randomIntBetween(1, 5),
      page_size: 20,
    };
    if (Math.random() < 0.4) params.q = randomItem(SEARCH_TERMS);
    if (Math.random() < 0.3) params.category = randomItem(CATEGORIES);
    if (Math.random() < 0.3) params.job_type = randomItem(["fixed", "hourly"]);

    const start = Date.now();
    const resp = http.get(`${API}/jobs`, {
      headers: { "Content-Type": "application/json" },
      tags:    { name: "search" },
    });
    searchLatency.add(Date.now() - start);

    check(resp, {
      "jobs search 200": (r) => r.status === 200,
      "jobs has items":  (r) => {
        try { return Array.isArray(r.json("items")); } catch { return false; }
      },
    });

    // View a job detail (simulate click)
    if (resp.status === 200) {
      const jobs = resp.json("items") || [];
      if (jobs.length > 0) {
        const job = randomItem(jobs);
        const start2 = Date.now();
        const det = http.get(`${API}/jobs/${job.id}`, {
          tags: { name: "job_detail" },
        });
        jobViewLatency.add(Date.now() - start2);
        check(det, { "job detail 200": (r) => r.status === 200 });
      }
    }
  });

  sleep(randomIntBetween(2, 5));  // Think time

  group("Browse Freelancers", () => {
    const params = {};
    if (Math.random() < 0.5) params.q = randomItem(SKILLS);
    if (Math.random() < 0.3) params.experience_level = randomItem(["entry", "intermediate", "expert"]);

    const resp = http.get(`${API}/users/freelancers`, {
      tags: { name: "freelancers_search" },
    });
    check(resp, { "freelancers 200": (r) => r.status === 200 });
  });

  sleep(randomIntBetween(1, 4));

  // Occasional health check (monitoring)
  if (Math.random() < 0.1) {
    const h = http.get(`${API}/health`, { tags: { name: "health" } });
    check(h, { "health 200": (r) => r.status === 200 });
  }
}

// ── Scenario: authenticated user flow ─────────────────────────────────────
export function authScenario() {
  const role = Math.random() < 0.4 ? "client" : "freelancer";
  const user = register(role);
  if (!user) {
    sleep(5);
    return;
  }

  const headers = {
    "Content-Type":  "application/json",
    "Authorization": `Bearer ${user.token}`,
  };

  group("Authenticated Profile", () => {
    const me = http.get(`${API}/auth/me`, { headers, tags: { name: "me" } });
    check(me, { "get me 200": (r) => r.status === 200 });

    sleep(1);

    const notifs = http.get(`${API}/notifications/unread-count`, {
      headers,
      tags: { name: "unread_count" },
    });
    check(notifs, { "unread count 200": (r) => r.status === 200 });
  });

  sleep(randomIntBetween(1, 3));

  if (role === "client") {
    group("Client: Post Job", () => {
      const jobType = Math.random() < 0.5 ? "fixed" : "hourly";
      const payload = {
        title:              `Test Job ${randomIntBetween(1000, 9999)}`,
        description:        "Load test job — please ignore. مشروع اختبار الأداء.",
        category:           randomItem(CATEGORIES),
        job_type:           jobType,
        skills_required:    [randomItem(SKILLS), randomItem(SKILLS)],
        experience_level:   "intermediate",
        expected_duration:  "1_to_4_weeks",
        ...(jobType === "fixed"
          ? { fixed_price: randomIntBetween(100_000, 1_000_000) }
          : { budget_min: 100_000, budget_max: 500_000 }),
      };

      const resp = http.post(`${API}/jobs`, JSON.stringify(payload), {
        headers,
        tags: { name: "post_job" },
      });
      check(resp, { "post job 201": (r) => r.status === 201 });

      if (resp.status === 201) {
        sleep(1);
        // View my jobs
        const mine = http.get(`${API}/jobs/my/posted`, {
          headers,
          tags: { name: "my_jobs" },
        });
        check(mine, { "my jobs 200": (r) => r.status === 200 });
      }
    });
  } else {
    group("Freelancer: Search & View", () => {
      const search = http.get(`${API}/jobs?page=1&page_size=10`, {
        headers,
        tags: { name: "search" },
      });
      check(search, { "search 200": (r) => r.status === 200 });

      // View proposals
      const props = http.get(`${API}/proposals/my?page=1`, {
        headers,
        tags: { name: "my_proposals" },
      });
      check(props, { "proposals 200": (r) => r.status === 200 });
    });
  }

  sleep(randomIntBetween(2, 5));

  // Logout
  http.post(`${API}/auth/logout`, "{}", { headers, tags: { name: "logout" } });
}
