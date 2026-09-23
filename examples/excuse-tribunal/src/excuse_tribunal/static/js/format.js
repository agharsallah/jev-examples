// Pure formatting: numbers in, the words and widths the court uses out.
export const pct = (p) => `${Math.round(p * 100)}%`;
/** A 0-4 score as a bar width in percent, clamped so a stray value cannot overflow. */
export const barWidth = (value) => Math.max(0, Math.min(1, value / 4)) * 100;
/** "2026-09-23T14:05:11+00:00" -> "2026-09-23 14:05". */
export const hearingTime = (iso) => iso.slice(0, 16).replace("T", " ");
export const recordStats = (s) => `${s.hearings} hearings · average believability ${s.average_believability.toFixed(2)} / 4 · signature move: ${s.signature_move}`;
