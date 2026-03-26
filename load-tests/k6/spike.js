/**
 * Kaasb — k6 Spike Test
 * ======================
 * Simulates sudden 10× traffic spike — like a viral post or news mention.
 * Tests whether the system recovers gracefully after the spike ends.
 *
 * Iraqi scenario: platform featured on a popular Iraqi tech page → sudden flood.
 *
 * Pass criteria:
 *   - During spike: error rate < 10% (some degradation is acceptable)
 *   - After spike (recovery): error rate returns to < 1% within 2 minutes
 *   - System does NOT require manual restart to recover
 *
 * Run:
 *   k6 run --env BASE_URL=https://kaasb.com spike.js
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Gauge } from "k6/metrics";
import { randomItem, randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API      = `${BASE_URL}/api/v1`;

const errorRate   = new Rate("error_rate");
const activeUsers = new Gauge("active_users");

export const options = {
  stages: [
    { duration: "2m",  target: 10  },   // Baseline normal traffic
    { duration: "1m",  target: 10  },   // Steady state
    { duration: "30s", target: 500 },   // SPIKE — 10× in 30 seconds
    { duration: "2m",  target: 500 },   // Hold the spike
    { duration: "1m",  target: 10  },   // DROP back to normal
    { duration: "3m",  target: 10  },   // Recovery period — watch error rate recover
    { duration: "1m",  target: 0   },   // Cooldown
  ],

  thresholds: {
    http_req_failed:           ["rate<0.10"],     // Up to 10% errors during spike is acceptable
    http_req_duration:         ["p(95)<10000"],   // p95 can go up to 10s during spike
    // Post-spike recovery (last 3 min must be normal)
    // Checked manually in analysis
  },
};

const CATEGORIES = ["Web Development", "Mobile Development", "UI/UX Design", "Translation"];
const SKILLS     = ["Python", "React", "Flutter", "مطور", "JavaScript", "Node.js"];

export default function () {
  activeUsers.add(1);

  // During a viral spike, most traffic is anonymous first-time visitors
  // browsing quickly — short sessions, lots of search queries
  const action = Math.random();

  if (action < 0.70) {
    // Quick anonymous browse
    const r = http.get(
      `${API}/jobs?page=${randomIntBetween(1, 3)}&page_size=20`,
      { tags: { name: "spike_browse" } },
    );
    errorRate.add(r.status >= 400);
    check(r, {
      "spike browse ok":      (x) => x.status === 200,
      "not 503":              (x) => x.status !== 503,
      "not 502":              (x) => x.status !== 502,
    });

    if (r.status === 200) {
      const jobs = r.json("items") || [];
      if (jobs.length > 0) {
        sleep(0.5);  // Short think time — spike visitors scan fast
        const j = randomItem(jobs);
        const det = http.get(`${API}/jobs/${j.id}`, { tags: { name: "spike_detail" } });
        errorRate.add(det.status >= 400);
        check(det, { "spike detail ok": (x) => x.status === 200 });
      }
    }

  } else if (action < 0.90) {
    // Quick freelancer browse
    const r = http.get(
      `${API}/users/freelancers?page=1&page_size=10`,
      { tags: { name: "spike_freelancers" } },
    );
    errorRate.add(r.status >= 400);
    check(r, { "spike freelancers ok": (x) => x.status === 200 });

  } else {
    // Some users try to register during spike
    const n = `${Date.now()}_${randomIntBetween(1, 999999)}`;
    const resp = http.post(
      `${API}/auth/register`,
      JSON.stringify({
        email:        `spike_${n}@loadtest.kaasb.com`,
        username:     `spike${n}`.slice(0, 30),
        password:     "TestPass123!@#",
        first_name:   "Spike",
        last_name:    "User",
        primary_role: "freelancer",
      }),
      {
        headers: { "Content-Type": "application/json" },
        tags:    { name: "spike_register" },
      },
    );
    errorRate.add(resp.status >= 400);
    check(resp, { "spike register 2xx": (r) => r.status >= 200 && r.status < 300 });
  }

  // Very short think time during spike — users are impatient
  sleep(randomIntBetween(0, 2));
  activeUsers.add(-1);
}
