/**
 * Kaasb — k6 Breakpoint Test
 * ===========================
 * Continuously increases load until the system breaks.
 * Documents the exact breaking point (users, RPS, p95 at failure).
 *
 * IMPORTANT: This WILL break your system. Only run on staging or
 * dedicated test environment. Never on production.
 *
 * Breaking point = when ANY of these conditions is first met:
 *   - Error rate exceeds 5%
 *   - p95 exceeds 10 seconds
 *   - System returns sustained 503/502 responses
 *
 * Run:
 *   k6 run --env BASE_URL=http://staging.kaasb.com breakpoint.js \
 *          --out csv=reports/breakpoint.csv
 *
 * After the test, check reports/breakpoint.csv for the exact
 * timestamp when thresholds were first violated.
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";
import { randomItem, randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API      = `${BASE_URL}/api/v1`;

const errorRate     = new Rate("error_rate");
const p95live       = new Trend("breakpoint_p95", true);
const serverErrors  = new Counter("server_errors_5xx");
const systemDown    = new Counter("system_down_503");

export const options = {
  // Ramp up 10 users every 2 minutes — observe where system breaks
  stages: [
    { duration: "2m",  target: 10  },
    { duration: "2m",  target: 20  },
    { duration: "2m",  target: 40  },
    { duration: "2m",  target: 60  },
    { duration: "2m",  target: 80  },
    { duration: "2m",  target: 100 },
    { duration: "2m",  target: 150 },
    { duration: "2m",  target: 200 },
    { duration: "2m",  target: 300 },
    { duration: "2m",  target: 400 },
    { duration: "2m",  target: 500 },
    { duration: "2m",  target: 700 },
    { duration: "2m",  target: 1000 },
    // Recovery — important to check system recovers after overload
    { duration: "5m",  target: 50  },
    { duration: "3m",  target: 0   },
  ],

  // These thresholds will FAIL — that's the point.
  // The test runner records WHEN they fail.
  thresholds: {
    http_req_failed:  ["rate<0.05"],    // Breaking point: 5% errors
    http_req_duration: ["p(95)<10000"], // Breaking point: p95 > 10s
    error_rate:        ["rate<0.05"],
  },
};

const CATEGORIES = ["Web Development", "Mobile Development", "UI/UX Design"];
const SEARCH_TERMS = ["Python", "React", "مطور", "design", "Flutter"];

export default function () {
  const vus = __VU;

  // Vary request mix based on load level to simulate realistic breakdown
  const action = Math.random();

  if (action < 0.60) {
    // Most traffic: search
    const r = http.get(
      `${API}/jobs?page=${randomIntBetween(1, 3)}&page_size=20`,
      { tags: { name: "search" } },
    );
    p95live.add(r.timings.duration);
    errorRate.add(r.status >= 400);

    if (r.status >= 500) {
      serverErrors.add(1);
      console.log(`SERVER ERROR at ${vus} VUs: ${r.status} on search`);
    }
    if (r.status === 503) {
      systemDown.add(1);
      console.log(`SYSTEM DOWN at ${vus} VUs: 503 on search`);
    }

    check(r, {
      "not down":      (x) => x.status !== 503,
      "not gateway":   (x) => x.status !== 502,
      "search ok":     (x) => x.status === 200,
    });

    if (r.status === 200) {
      const jobs = r.json("items") || [];
      if (jobs.length > 0) {
        sleep(0.5);
        const det = http.get(`${API}/jobs/${randomItem(jobs).id}`, {
          tags: { name: "detail" },
        });
        p95live.add(det.timings.duration);
        errorRate.add(det.status >= 400);
        if (det.status >= 500) serverErrors.add(1);
      }
    }

  } else if (action < 0.80) {
    // Auth: register (DB write — bottleneck under load)
    const n = `${Date.now()}_${__VU}_${randomIntBetween(1, 9999)}`;
    const resp = http.post(
      `${API}/auth/register`,
      JSON.stringify({
        email:        `bp_${n}@loadtest.kaasb.com`,
        username:     `bp${n}`.slice(0, 30),
        password:     "TestPass123!@#",
        first_name:   "Break",
        last_name:    "Point",
        primary_role: "freelancer",
      }),
      { headers: { "Content-Type": "application/json" }, tags: { name: "register" } },
    );
    p95live.add(resp.timings.duration);
    errorRate.add(resp.status >= 400);
    if (resp.status >= 500) serverErrors.add(1);
    if (resp.status === 503) systemDown.add(1);

    check(resp, { "register not 5xx": (r) => r.status < 500 });

  } else {
    // Health check — measures system liveness under load
    const h = http.get(`${API}/health`, { tags: { name: "health" } });
    p95live.add(h.timings.duration);

    if (h.status === 503) {
      systemDown.add(1);
      console.log(`HEALTH CHECK FAILED at ${vus} VUs: 503`);
    }

    check(h, {
      "system alive":      (x) => x.status === 200,
      "not degraded":      (x) => x.status !== 503,
    });

    // Read freelancers (JOIN query — heavier than job search)
    const fr = http.get(`${API}/users/freelancers?page=1`, {
      tags: { name: "freelancers" },
    });
    p95live.add(fr.timings.duration);
    errorRate.add(fr.status >= 400);
    if (fr.status >= 500) serverErrors.add(1);
  }

  // No sleep — maximize pressure
  sleep(Math.random() < 0.3 ? 0 : 1);
}

export function handleSummary(data) {
  const stats = data.metrics;

  let breakingPoint = null;
  let maxVUs = 0;
  let finalErrorRate = 0;

  if (stats.vus_max) {
    maxVUs = stats.vus_max.values.max;
  }
  if (stats.error_rate) {
    finalErrorRate = stats.error_rate.values.rate;
  }

  const p95 = stats.http_req_duration?.values["p(95)"] || 0;

  const summary = {
    test:           "breakpoint",
    timestamp:      new Date().toISOString(),
    max_vus_tested: maxVUs,
    final_error_rate_pct: (finalErrorRate * 100).toFixed(2),
    p95_ms:         p95.toFixed(0),
    server_errors:  stats.server_errors_5xx?.values.count || 0,
    system_down:    stats.system_down_503?.values.count || 0,
    conclusion: finalErrorRate > 0.05
      ? `BREAKING POINT REACHED — system degraded under ~${maxVUs} VUs`
      : `System held up to ${maxVUs} VUs without breaking`,
  };

  console.log("\n" + "=".repeat(60));
  console.log("  BREAKPOINT TEST RESULTS");
  console.log("=".repeat(60));
  console.log(JSON.stringify(summary, null, 2));
  console.log("=".repeat(60) + "\n");

  return {
    "reports/breakpoint_summary.json": JSON.stringify(summary, null, 2),
  };
}
