import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8000";

export const options = {
  stages: [
    { duration: "30s", target: 10 },
    { duration: "1m", target: 30 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.001"],
    http_req_duration: ["p(95)<150"],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/health`);
  check(res, {
    "health status is 200": (r) => r.status === 200,
    "health body has ok": (r) => r.body && r.body.includes("ok"),
  });
  sleep(1);
}

