const tokenBuckets = new Map<string, { tokens: number; lastRefill: number }>();

const CLEANUP_INTERVAL = 60_000;
let lastCleanup = Date.now();

function cleanup() {
  const now = Date.now();
  if (now - lastCleanup < CLEANUP_INTERVAL) return;
  lastCleanup = now;
  for (const [key, bucket] of tokenBuckets) {
    if (now - bucket.lastRefill > 120_000) {
      tokenBuckets.delete(key);
    }
  }
}

export function rateLimit(
  key: string,
  { maxTokens = 5, refillInterval = 60_000 } = {}
): { success: boolean; remaining: number } {
  cleanup();

  const now = Date.now();
  let bucket = tokenBuckets.get(key);

  if (!bucket) {
    bucket = { tokens: maxTokens, lastRefill: now };
    tokenBuckets.set(key, bucket);
  }

  const elapsed = now - bucket.lastRefill;
  if (elapsed >= refillInterval) {
    bucket.tokens = maxTokens;
    bucket.lastRefill = now;
  }

  if (bucket.tokens <= 0) {
    return { success: false, remaining: 0 };
  }

  bucket.tokens -= 1;
  return { success: true, remaining: bucket.tokens };
}
