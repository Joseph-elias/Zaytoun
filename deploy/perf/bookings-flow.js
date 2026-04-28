import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8000";
const FARMER_PHONE = __ENV.FARMER_PHONE || "";
const FARMER_PASSWORD = __ENV.FARMER_PASSWORD || "";
const WORKER_PHONE = __ENV.WORKER_PHONE || "";
const WORKER_PASSWORD = __ENV.WORKER_PASSWORD || "";
const WORKER_ID = __ENV.WORKER_ID || "";
const rateLimitHits = new Counter("rate_limit_hits");

export const options = {
  scenarios: {
    booking_flow: {
      executor: "ramping-vus",
      stages: [
        { duration: "1m", target: 5 },
        { duration: "2m", target: 15 },
        { duration: "1m", target: 0 },
      ],
      gracefulRampDown: "30s",
    },
  },
  thresholds: {
    checks: ["rate>0.95"],
    "http_req_duration{type:booking_create}": ["p(95)<1000"],
    "http_req_duration{type:booking_worker_response}": ["p(95)<1000"],
    "http_req_duration{type:booking_farmer_confirm}": ["p(95)<1000"],
    "rate_limit_hits{type:booking_create}": ["count<1500"],
    "rate_limit_hits{type:booking_worker_response}": ["count<1500"],
    "rate_limit_hits{type:booking_farmer_confirm}": ["count<1500"],
  },
};

http.setResponseCallback(http.expectedStatuses(200, 201, 400, 401, 403, 404, 429));

function login(phone, password) {
  const res = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({
      phone,
      password,
      legal_acknowledged: true,
    }),
    { headers: { "Content-Type": "application/json" } },
  );
  if (res.status !== 200) {
    return null;
  }
  const body = res.json();
  if (body && body.access_token) {
    return body.access_token;
  }
  return null;
}

function authHeaders(token) {
  return {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  };
}

function authHeadersWithTags(token, typeTag) {
  const base = authHeaders(token);
  return {
    headers: base.headers,
    tags: { type: typeTag },
  };
}

export function setup() {
  if (!WORKER_ID) {
    throw new Error("WORKER_ID is required");
  }
  const farmerToken = login(FARMER_PHONE, FARMER_PASSWORD);
  const workerToken = login(WORKER_PHONE, WORKER_PASSWORD);
  if (!farmerToken || !workerToken) {
    throw new Error("Could not obtain setup auth tokens");
  }
  return { farmerToken, workerToken };
}

export default function (data) {
  const farmerToken = data.farmerToken;
  const workerToken = data.workerToken;

  const workDate = "2026-05-01";
  const createRes = http.post(
    `${BASE_URL}/workers/${WORKER_ID}/bookings`,
    JSON.stringify({
      note: "perf-baseline",
      requests: [{ work_date: workDate, work_slot: "full_day", requested_men: 1, requested_women: 0 }],
    }),
    authHeadersWithTags(farmerToken, "booking_create"),
  );
  if (createRes.status === 429) {
    rateLimitHits.add(1, { type: "booking_create" });
  }

  check(createRes, {
    "booking create status known": (r) => [201, 400, 401, 403, 404, 429].includes(r.status),
  });

  if (createRes.status !== 201) {
    sleep(1);
    return;
  }

  const created = createRes.json();
  const bookingId = Array.isArray(created) && created.length > 0 ? created[0].id : null;
  if (!bookingId) {
    sleep(1);
    return;
  }

  const workerDecision = http.patch(
    `${BASE_URL}/bookings/${bookingId}/worker-response`,
    JSON.stringify({ action: "accept" }),
    authHeadersWithTags(workerToken, "booking_worker_response"),
  );
  if (workerDecision.status === 429) {
    rateLimitHits.add(1, { type: "booking_worker_response" });
  }
  check(workerDecision, {
    "worker response status known": (r) => [200, 400, 401, 403, 404, 429].includes(r.status),
  });

  if (workerDecision.status === 200) {
    const farmerConfirm = http.patch(
      `${BASE_URL}/bookings/${bookingId}/farmer-validation`,
      JSON.stringify({ action: "confirm" }),
      authHeadersWithTags(farmerToken, "booking_farmer_confirm"),
    );
    if (farmerConfirm.status === 429) {
      rateLimitHits.add(1, { type: "booking_farmer_confirm" });
    }
    check(farmerConfirm, {
      "farmer confirmation status known": (r) => [200, 400, 401, 403, 404, 429].includes(r.status),
    });
  }

  sleep(1);
}
