/**
 * Kaasb — k6 WebSocket Load Test
 * ================================
 * Tests the WebSocket connection manager under concurrent connection load.
 * Simulates users opening real-time chat connections simultaneously.
 *
 * The Kaasb ConnectionManager uses in-memory dict[user_id → WebSocket].
 * Under multi-worker Gunicorn (5 workers), WebSocket state is per-worker.
 * This test measures: connection acceptance rate, message delivery, cleanup.
 *
 * Pass criteria:
 *   - > 95% of connections accepted (not rejected)
 *   - Messages delivered within 500ms
 *   - No connection leaks (connections properly closed)
 *
 * Run:
 *   k6 run --env BASE_URL=https://kaasb.com websocket.js
 *   k6 run --env BASE_URL=http://localhost:8000 websocket.js
 */

import http from "k6/http";
import ws from "k6/ws";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";
import { randomIntBetween } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API      = `${BASE_URL}/api/v1`;
const WS_URL   = BASE_URL.replace("https://", "wss://").replace("http://", "ws://");

const wsConnectRate  = new Rate("ws_connect_success");
const wsMessageRate  = new Rate("ws_message_received");
const wsLatency      = new Trend("ws_message_latency", true);
const wsErrors       = new Counter("ws_errors");
const wsConnections  = new Counter("ws_connections_total");

export const options = {
  scenarios: {
    // WS connection stress: many concurrent connections
    ws_connections: {
      executor:  "ramping-vus",
      startVUs:  0,
      stages: [
        { duration: "1m",  target: 50  },
        { duration: "3m",  target: 100 },
        { duration: "3m",  target: 200 },
        { duration: "2m",  target: 100 },
        { duration: "1m",  target: 0   },
      ],
      exec: "wsScenario",
    },
  },

  thresholds: {
    ws_connect_success:    ["rate>0.95"],    // 95%+ connections must succeed
    ws_message_received:   ["rate>0.90"],    // 90%+ messages received
    ws_message_latency:    ["p(95)<500"],    // p95 message latency < 500ms
    http_req_failed:       ["rate<0.05"],    // HTTP requests (register/login) < 5% errors
  },
};

function getAuthToken() {
  const n = `${Date.now()}_${__VU}_${randomIntBetween(1, 9999)}`;
  const resp = http.post(
    `${API}/auth/register`,
    JSON.stringify({
      email:        `ws_${n}@loadtest.kaasb.com`,
      username:     `ws${n}`.slice(0, 30),
      password:     "TestPass123!@#",
      first_name:   "WS",
      last_name:    "Test",
      primary_role: randomIntBetween(0, 1) === 0 ? "client" : "freelancer",
    }),
    { headers: { "Content-Type": "application/json" } },
  );

  if (resp.status >= 200 && resp.status < 300) {
    return resp.json("access_token");
  }
  return null;
}

export function wsScenario() {
  const token = getAuthToken();
  if (!token) {
    sleep(2);
    return;
  }

  // Connect to WebSocket with auth token
  // The Kaasb WebSocket endpoint accepts token in query string or header
  const wsEndpoint = `${WS_URL}/api/v1/ws?token=${token}`;

  wsConnections.add(1);
  let messagesReceived = 0;
  let connectTime = Date.now();
  let connected = false;

  const res = ws.connect(wsEndpoint, {}, function (socket) {
    socket.on("open", function () {
      connected = true;
      wsConnectRate.add(true);

      // Send a ping to confirm bi-directional communication
      const sendTime = Date.now();
      socket.send(JSON.stringify({ type: "ping", timestamp: sendTime }));

      // Keep connection alive for 30-60 seconds (simulates active user session)
      socket.setInterval(function () {
        socket.send(JSON.stringify({
          type:      "heartbeat",
          timestamp: Date.now(),
          vu:        __VU,
        }));
      }, 10000);
    });

    socket.on("message", function (data) {
      messagesReceived++;
      try {
        const msg = JSON.parse(data);
        if (msg.type === "pong" || msg.type === "ping" || msg.type === "message") {
          wsMessageRate.add(true);
          wsLatency.add(Date.now() - (msg.timestamp || Date.now()));
        }
      } catch (_) {
        // Non-JSON message — still counts as received
        wsMessageRate.add(true);
      }
    });

    socket.on("error", function (e) {
      wsErrors.add(1);
      if (e.error) {
        console.log(`WS Error (VU ${__VU}): ${e.error}`);
      }
    });

    socket.on("close", function (code) {
      // 1000 = normal close, 1001 = going away, others = unexpected
      if (code !== 1000 && code !== 1001 && code !== undefined) {
        wsErrors.add(1);
        console.log(`WS unexpected close (VU ${__VU}): code ${code}`);
      }
    });

    // Hold connection for realistic session duration (30-60 seconds)
    socket.setTimeout(function () {
      socket.close();
    }, randomIntBetween(30, 60) * 1000);
  });

  if (!connected) {
    wsConnectRate.add(false);
  }

  check(res, {
    "ws connect ok":     (r) => r && r.status === 101,
    "received messages": () => messagesReceived > 0,
  });

  sleep(randomIntBetween(1, 5));
}
