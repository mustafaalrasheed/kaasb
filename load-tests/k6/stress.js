/**
 * Kaasb — k6 Stress Test
 * =======================
 * Gradually increases load to 3× normal (150 users), looking for
 * the degradation point where response times or error rates rise.
 *
 * Pass criteria: system stays within thresholds up to 3× normal.
 *
 * Run:
 *   k6 run --env BASE_URL=https://kaasb.com stress.js
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { randomItem, randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API      = `${BASE_URL}/api/v1`;

const errorRate = new Rate("error_rate");
const p95trend  = new Trend("stress_p95", true);

export const options = {
  stages: [
    { duration: "2m",  target: 10  },   // Warm up — normal load
    { duration: "5m",  target: 50  },   // 1× normal
    { duration: "5m",  target: 100 },   // 2× — first stress tier
    { duration: "5m",  target: 150 },   // 3× — target stress level
    { duration: "5m",  target: 200 },   // 4× — find breaking point
    { duration: "5m",  target: 250 },   // 5× — maximum stress
    { duration: "5m",  target: 100 },   // Recovery: drop back to 2×
    { duration: "3m",  target: 0   },   // Cooldown
  ],

  thresholds: {
    http_req_failed:  ["rate<0.05"],    // Allow up to 5% under stress (stricter: 1% at normal)
    http_req_duration: ["p(95)<5000"],  // p95 must stay under 5s even under stress
    error_rate:        ["rate<0.05"],
  },
};

const SEARCH_TERMS = ["Python", "React", "مطور", "design", "Flutter", "Django"];
const CATEGORIES   = ["Web Development", "Mobile Development", "UI/UX Design"];

function register(role) {
  const n = `${Date.now()}_${randomIntBetween(1, 999999)}`;
  const resp = http.post(
    `${API}/auth/register`,
    JSON.stringify({
      email:        `stress_${n}@loadtest.kaasb.com`,
      username:     `stress${n}`.slice(0, 30),
      password:     "TestPass123!@#",
      first_name:   "Stress",
      last_name:    "Test",
      primary_role: role,
    }),
    { headers: { "Content-Type": "application/json" }, tags: { name: "register" } },
  );
  if (resp.status >= 200 && resp.status < 300) {
    return resp.json("access_token");
  }
  return null;
}

export default function () {
  const scenario = Math.random();

  if (scenario < 0.55) {
    // Anonymous browse
    group("Anonymous Browse", () => {
      const params = new URLSearchParams({ page: "1", page_size: "20" });
      if (Math.random() < 0.4) params.set("q", randomItem(SEARCH_TERMS));
      if (Math.random() < 0.3) params.set("category", randomItem(CATEGORIES));

      const r = http.get(`${API}/jobs?${params}`, { tags: { name: "search" } });
      errorRate.add(r.status >= 400);
      p95trend.add(r.timings.duration);
      check(r, { "search ok": (x) => x.status === 200 });

      if (r.status === 200) {
        const jobs = r.json("items") || [];
        if (jobs.length > 0) {
          const job = randomItem(jobs);
          const det = http.get(`${API}/jobs/${job.id}`, { tags: { name: "job_detail" } });
          errorRate.add(det.status >= 400);
          check(det, { "detail ok": (x) => x.status === 200 });
        }
      }

      sleep(randomIntBetween(1, 3));

      const fr = http.get(`${API}/users/freelancers?page=1`, { tags: { name: "freelancers" } });
      errorRate.add(fr.status >= 400);
      check(fr, { "freelancers ok": (x) => x.status === 200 });
    });

  } else if (scenario < 0.80) {
    // Authenticated user
    group("Auth Flow", () => {
      const role  = Math.random() < 0.4 ? "client" : "freelancer";
      const token = register(role);
      if (!token) { sleep(2); return; }

      const headers = {
        "Content-Type":  "application/json",
        "Authorization": `Bearer ${token}`,
      };

      const me = http.get(`${API}/auth/me`, { headers, tags: { name: "me" } });
      errorRate.add(me.status >= 400);
      check(me, { "me ok": (x) => x.status === 200 });

      sleep(1);

      const notif = http.get(`${API}/notifications/unread-count`, {
        headers,
        tags: { name: "notifications" },
      });
      errorRate.add(notif.status >= 400);

      if (role === "freelancer") {
        sleep(1);
        const props = http.get(`${API}/proposals/my?page=1`, {
          headers,
          tags: { name: "my_proposals" },
        });
        errorRate.add(props.status >= 400);
      }
    });

  } else {
    // Post job (client action — most resource intensive)
    group("Post Job", () => {
      const token = register("client");
      if (!token) { sleep(3); return; }

      const headers = {
        "Content-Type":  "application/json",
        "Authorization": `Bearer ${token}`,
      };

      const jobType = Math.random() < 0.5 ? "fixed" : "hourly";
      const resp = http.post(
        `${API}/jobs`,
        JSON.stringify({
          title:             `Stress Test Job ${randomIntBetween(1, 99999)}`,
          description:       "Stress test — ignore. مشروع اختبار.",
          category:          randomItem(CATEGORIES),
          job_type:          jobType,
          skills_required:   ["Python", "JavaScript"],
          experience_level:  "intermediate",
          expected_duration: "1_to_4_weeks",
          ...(jobType === "fixed"
            ? { fixed_price: 500_000 }
            : { budget_min: 200_000, budget_max: 800_000 }),
        }),
        { headers, tags: { name: "post_job" } },
      );
      errorRate.add(resp.status >= 400);
      check(resp, { "post job 2xx": (r) => r.status >= 200 && r.status < 300 });

      p95trend.add(resp.timings.duration);
    });
  }

  sleep(randomIntBetween(1, 3));
}
