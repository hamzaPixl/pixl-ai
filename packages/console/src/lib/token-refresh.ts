const TOKEN_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const REFRESH_BUFFER_MS = 5 * 60 * 1000; // Refresh 5 min before expiry
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 10_000; // 10 seconds between retries

let refreshTimer: ReturnType<typeof setTimeout> | null = null;
let onLogout: (() => void) | null = null;
let tokenIssuedAt: number | null = null;

/** Returns "ok" on success, "auth_failed" on 401, "error" on transient failure. */
async function doRefresh(): Promise<"ok" | "auth_failed" | "error"> {
  try {
    const res = await fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
    });
    if (res.ok) return "ok";
    if (res.status === 401) return "auth_failed";
    return "error";
  } catch {
    return "error";
  }
}

async function refreshWithRetry(): Promise<boolean> {
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    const result = await doRefresh();
    if (result === "ok") return true;
    if (result === "auth_failed") return false; // Don't retry on hard 401
    if (attempt < MAX_RETRIES - 1) {
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
    }
  }
  return false;
}

export function startTokenRefresh(logoutCallback: () => void, serverIssuedAt?: number): void {
  onLogout = logoutCallback;
  // serverIssuedAt is a Unix timestamp (seconds) from the JWT iat claim.
  // Convert to ms. Fall back to "now" for fresh logins.
  tokenIssuedAt = serverIssuedAt ? serverIssuedAt * 1000 : Date.now();
  scheduleRefresh();
}

export function stopTokenRefresh(): void {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
  onLogout = null;
  tokenIssuedAt = null;
}

function scheduleRefresh(): void {
  if (refreshTimer) clearTimeout(refreshTimer);

  // so page reloads mid-session still refresh before expiry.
  const elapsed = tokenIssuedAt ? Date.now() - tokenIssuedAt : 0;
  const timeUntilExpiry = TOKEN_TTL_MS - elapsed;
  const delay = Math.max(timeUntilExpiry - REFRESH_BUFFER_MS, 0);

  refreshTimer = setTimeout(async () => {
    const success = await refreshWithRetry();
    if (success) {
      tokenIssuedAt = Date.now();
      scheduleRefresh();
    } else {
      onLogout?.();
    }
  }, delay);
}
