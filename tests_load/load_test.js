import http from "k6/http";
import { sleep, check } from "k6";

export const options = {
  stages: [
    // 1. Ramp up
    { duration: "30s", target: 50 },
    // 2. Steady load
    { duration: "2m", target: 50 },
    // 3. Spike test
    { duration: "10s", target: 200 },
    // 4. Cooldown
    { duration: "20s", target: 0 },
  ],
  thresholds: {
    // 95% of requests must complete under 200ms
    http_req_duration: ["p(95)<200"],
    // Error rate must be less than 1%
    http_req_failed: ["rate<0.01"],
  },
};

const BASE_URL = __ENV.TARGET_URL || "http://localhost:8000";

export default function () {
  // Check health endpoint
  const resHealth = http.get(`${BASE_URL}/health`);
  check(resHealth, {
    "health status is 200": (r) => r.status === 200,
    "health service is up": (r) => r.json().status === "healthy",
  });

  sleep(1);
}
