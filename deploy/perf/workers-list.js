import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8000";
const rateLimitHits = new Counter("rate_limit_hits");

export const options = {
  stages: [
    { duration: "1m", target: 20 },
    { duration: "2m", target: 80 },
    { duration: "1m", target: 120 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    checks: ["rate>0.99"],
    "http_req_duration{type:workers_no_filter}": ["p(95)<500"],
    "http_req_duration{type:workers_filtered}": ["p(95)<1000"],
    "rate_limit_hits{type:workers_no_filter}": ["count<5000"],
    "rate_limit_hits{type:workers_filtered}": ["count<5000"],
  },
};

http.setResponseCallback(http.expectedStatuses(200, 401, 403, 429));

function withAuthHeaders() {
  const token = __ENV.BEARER_TOKEN || "";
  if (!token) {
    return {};
  }
  return { headers: { Authorization: `Bearer ${token}` } };
}

export default function () {
  const noFilter = http.get(`${BASE_URL}/workers`, withAuthHeaders(), { tags: { type: "workers_no_filter" } });
  if (noFilter.status === 429) {
    rateLimitHits.add(1, { type: "workers_no_filter" });
  }
  check(noFilter, {
    "workers (no filter) known status": (r) => [200, 401, 403, 429].includes(r.status),
  });

  const filtered = http.get(
    `${BASE_URL}/workers?available=true&village=${encodeURIComponent(__ENV.TEST_VILLAGE || "Sfax")}&work_date=2026-05-01&work_slot=full_day`,
    withAuthHeaders(),
    { tags: { type: "workers_filtered" } },
  );
  if (filtered.status === 429) {
    rateLimitHits.add(1, { type: "workers_filtered" });
  }
  check(filtered, {
    "workers (filtered) known status": (r) => [200, 401, 403, 429].includes(r.status),
  });

  sleep(1);
}
