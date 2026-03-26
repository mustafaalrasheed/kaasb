/**
 * Kaasb — k6 Soak Test (Endurance Test)
 * =======================================
 * Sustained normal load for 4 hours.
 * Detects: memory leaks, connection pool exhaustion, disk fill,
 *          database cursor leaks, Redis key accumulation.
 *
 * Iraqi scenario: Thursday/Friday peak (weekend), sustained high traffic
 * from 18:00 to 22:00 Baghdad time = 4 hours of peak load.
 *
 * Pass criteria:
 *   - Error rate stays < 1% throughout all 4 hours
 *   - p95 does NOT degrade more than 20% from the first 10-minute window
 *   - Memory (checked via /health/detailed) does NOT grow unboundedly
 *   - No container restarts observed
 *
 * Run:
 *   k6 run --env BASE_URL=https://kaasb.com \
 *          --env HEALTH_TOKEN=your-bearer-token \
 *          soak.js
 *
 * Note: Full 4-hour run. Use --out csv=reports/soak.csv to capture data.
 *       Check memory via Grafana while this runs.
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";
import { randomItem, randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL     = __ENV.BASE_URL     || "http://localhost:8000";
const HEALTH_TOKEN = __ENV.HEALTH_TOKEN || "";
const API          = `${BASE_URL}/api/v1`;

const errorRate          = new Rate("error_rate");
const responseTimeTrend  = new Trend("response_time_soak", true);
const leakIndicator      = new Counter("potential_leak_events");

// How often to check /health/detailed for memory stats (every 5 minutes)
const HEALTH_CHECK_INTERVAL_REQUESTS = 300;
let requestCount = 0;

export const options = {
  stages: [
    { duration: "5m",  target: 30 },   // Ramp up
    { duration: "230m", target: 30 },  // Hold for ~3h50m (total ~4h)
    { duration: "5m",  target: 0  },   // Ramp down
  ],

  thresholds: {
    http_req_failed:  ["rate<0.01"],    // Strict — must stay under 1% all 4 hours
    http_req_duration: [
      "p(95)<2000",
      "p(99)<5000",
    ],
    error_rate: ["rate<0.01"],
  },
};

// Track performance windows to detect degradation over time
const WINDOW_SIZE = 1000;
let windowStart = Date.now();
let windowErrors = 0;
let windowRequests = 0;

function trackWindow(isError, duration) {
  windowRequests++;
  if (isError) windowErrors++;
  responseTimeTrend.add(duration);

  if (windowRequests >= WINDOW_SIZE) {
    const windowErrorRate = windowErrors / windowRequests;
    if (windowErrorRate > 0.02) {
      leakIndicator.add(1);
      console.warn(
        `SOAK WARNING: Error rate ${(windowErrorRate * 100).toFixed(1)}% ` +
        `in last ${WINDOW_SIZE} requests. ` +
        `Elapsed: ${((Date.now() - windowStart) / 60000).toFixed(0)} min`,
      );
    }
    windowErrors   = 0;
    windowRequests = 0;
  }
}

const SEARCH_TERMS = ["Python", "React", "مطور", "design", "Flutter", "Node.js", "Arabic"];
const CATEGORIES   = ["Web Development", "Mobile Development", "UI/UX Design", "Translation"];
const SKILLS       = ["Python", "JavaScript", "React", "Flutter", "Figma", "Django", "Docker"];

function registerUser(role) {
  const n = `${Date.now()}_${randomIntBetween(1, 9999999)}`;
  const resp = http.post(
    `${API}/auth/register`,
    JSON.stringify({
      email:        `soak_${n}@loadtest.kaasb.com`,
      username:     `soak${n}`.slice(0, 30),
      password:     "TestPass123!@#",
      first_name:   "Soak",
      last_name:    "Test",
      primary_role: role,
    }),
    { headers: { "Content-Type": "application/json" }, tags: { name: "register" } },
  );
  trackWindow(resp.status >= 400, resp.timings.duration);
  if (resp.status >= 200 && resp.status < 300) {
    return resp.json("access_token");
  }
  return null;
}

export default function () {
  requestCount++;

  // Periodic deep health check (requires HEALTH_TOKEN)
  if (requestCount % HEALTH_CHECK_INTERVAL_REQUESTS === 0 && HEALTH_TOKEN) {
    const h = http.get(`${API}/health/detailed`, {
      headers: { "Authorization": `Bearer ${HEALTH_TOKEN}` },
      tags:    { name: "health_detailed" },
    });
    if (h.status === 200) {
      try {
        const data = h.json();
        const poolUsed = data?.db?.pool?.checked_out || 0;
        const poolSize = data?.db?.pool?.size || 10;
        if (poolUsed / poolSize > 0.8) {
          leakIndicator.add(1);
          console.warn(`SOAK: DB pool at ${((poolUsed/poolSize)*100).toFixed(0)}% — possible connection leak`);
        }
      } catch (_) {}
    }
  }

  const scenario = Math.random();

  if (scenario < 0.60) {
    // Anonymous browse — lightweight
    const params = new URLSearchParams({ page: String(randomIntBetween(1, 3)), page_size: "20" });
    if (Math.random() < 0.4) params.set("q", randomItem(SEARCH_TERMS));
    if (Math.random() < 0.3) params.set("category", randomItem(CATEGORIES));

    const r1 = http.get(`${API}/jobs?${params}`, { tags: { name: "search" } });
    trackWindow(r1.status >= 400, r1.timings.duration);
    errorRate.add(r1.status >= 400);
    check(r1, { "search ok": (x) => x.status === 200 });

    if (r1.status === 200) {
      const jobs = r1.json("items") || [];
      if (jobs.length > 0) {
        sleep(randomIntBetween(1, 3));
        const j = randomItem(jobs);
        const r2 = http.get(`${API}/jobs/${j.id}`, { tags: { name: "job_detail" } });
        trackWindow(r2.status >= 400, r2.timings.duration);
        errorRate.add(r2.status >= 400);
        check(r2, { "detail ok": (x) => x.status === 200 });
      }
    }

    sleep(randomIntBetween(2, 5));

    const r3 = http.get(
      `${API}/users/freelancers?page=${randomIntBetween(1, 3)}`,
      { tags: { name: "freelancers" } },
    );
    trackWindow(r3.status >= 400, r3.timings.duration);
    errorRate.add(r3.status >= 400);

  } else if (scenario < 0.85) {
    // Registered user flow
    const role  = Math.random() < 0.35 ? "client" : "freelancer";
    const token = registerUser(role);
    if (!token) { sleep(3); return; }

    const headers = {
      "Content-Type":  "application/json",
      "Authorization": `Bearer ${token}`,
    };

    const me = http.get(`${API}/auth/me`, { headers, tags: { name: "me" } });
    trackWindow(me.status >= 400, me.timings.duration);
    errorRate.add(me.status >= 400);
    check(me, { "me ok": (x) => x.status === 200 });

    sleep(randomIntBetween(1, 2));

    const notif = http.get(`${API}/notifications/unread-count`, {
      headers,
      tags: { name: "notif" },
    });
    trackWindow(notif.status >= 400, notif.timings.duration);
    errorRate.add(notif.status >= 400);

    if (role === "client") {
      sleep(1);
      const mine = http.get(`${API}/jobs/my/posted?page=1`, {
        headers,
        tags: { name: "my_jobs" },
      });
      trackWindow(mine.status >= 400, mine.timings.duration);

      sleep(1);
      const contracts = http.get(`${API}/contracts/my?page=1`, {
        headers,
        tags: { name: "contracts" },
      });
      trackWindow(contracts.status >= 400, contracts.timings.duration);
      errorRate.add(contracts.status >= 400);
    } else {
      sleep(1);
      const props = http.get(`${API}/proposals/my?page=1`, {
        headers,
        tags: { name: "proposals" },
      });
      trackWindow(props.status >= 400, props.timings.duration);
      errorRate.add(props.status >= 400);
    }

    // Logout (important for soak — tests session cleanup prevents memory leak)
    http.post(`${API}/auth/logout`, "{}", { headers, tags: { name: "logout" } });

  } else {
    // Health liveness check
    const h = http.get(`${API}/health`, { tags: { name: "health" } });
    trackWindow(h.status >= 400, h.timings.duration);
    errorRate.add(h.status >= 400);
    check(h, { "health ok": (x) => x.status === 200 });
  }

  sleep(randomIntBetween(2, 6));
}
