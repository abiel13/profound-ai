/**
 * ProFund AI — API base URL (clean version)
 *
 * Priority:
 * 1. REACT_APP_BACKEND_URL (production / deployment)
 * 2. localhost fallback
 */

const API_BASE =
  process.env.REACT_APP_BACKEND_URL ||
  "http://localhost:8000";

export const API = `${API_BASE}/api`;

console.log("[ProFund] API base:", API_BASE);