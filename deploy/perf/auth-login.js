import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8000";
const LOGIN_PHONE = __ENV.LOGIN_PHONE || "";
const LOGIN_PASSWORD = __ENV.LOGIN_PASSWORD || "";
const rateLimitHits = new Counter("rate_limit_hits");

export const options = {
  stages: [
    { duration: "30s", target: 10 },
    { duration: "1m", target: 40 },
    { duration: "2m", target: 80 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    checks: ["rate>0.99"],
    "http_req_duration{type:auth_login}": ["p(95)<700"],
    "rate_limit_hits{type:auth_login}": ["count<3000"],
  },
};

http.setResponseCallback(http.expectedStatuses(200, 400, 401, 429));

export default function () {
  const payload = JSON.stringify({
    phone: LOGIN_PHONE,
    password: LOGIN_PASSWORD,
    legal_acknowledged: true,
  });

  const res = http.post(`${BASE_URL}/auth/login`, payload, {
    headers: { "Content-Type": "application/json" },
    tags: { type: "auth_login" },
  });
  if (res.status === 429) {
    rateLimitHits.add(1, { type: "auth_login" });
  }

  check(res, {
    "login returns known auth status": (r) => [200, 400, 401, 429].includes(r.status),
  });

  sleep(1);
}
