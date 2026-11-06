/** Millisecond durations stay compact; anything slower switches to seconds. */
export function formatDuration(durationMs: number): string {
  if (durationMs >= 1000) {
    return `${(durationMs / 1000).toFixed(1)} s`;
  }

  return `${durationMs} ms`;
}

/** UTC clock time keeps tests and server output independent of the locale. */
export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }

  return `${date.toISOString().slice(11, 19)} UTC`;
}
