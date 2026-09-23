/* How fast pieces fall: the chosen difficulty, sped up as rows are cleared. */

import type { Level } from "../api.js";

export const DEFAULT_LEVEL = "grandmaster";

// Both wells read the same ladder, so they always fall at the same speed.
let ladder: Level[] = [];
let current = DEFAULT_LEVEL;

export const setLadder = (levels: Level[]): void => void (ladder = levels);
export const setLevel = (key: string): void => void (current = key);
export const currentLevel = (): string => current;

/** Milliseconds per row for a well that has cleared `lines` rows so far. */
export function gravity(lines: number): number {
  const base = (ladder.find((l) => l.key === current) ?? { gravity_ms: 280 }).gravity_ms;
  const stage = Math.floor(lines / 10);
  return Math.max(90, Math.round(base * Math.pow(0.86, stage)));
}
