/**
 * Per-route rate limits are multiplied by THROTTLE_SCALE (default 1). Test environments that run the
 * integration suite repeatedly from one IP raise it; production leaves it unset.
 */
export const THROTTLE_SCALE = Math.max(1, Number(process.env.THROTTLE_SCALE ?? 1) || 1);
export const scaled = (n: number) => Math.ceil(n * THROTTLE_SCALE);
