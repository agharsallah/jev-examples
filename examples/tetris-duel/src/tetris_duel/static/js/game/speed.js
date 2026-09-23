/* How fast pieces fall: the chosen difficulty, sped up as rows are cleared. */
export const DEFAULT_LEVEL = "grandmaster";
// Both wells read the same ladder, so they always fall at the same speed.
let ladder = [];
let current = DEFAULT_LEVEL;
export const setLadder = (levels) => void (ladder = levels);
export const setLevel = (key) => void (current = key);
export const currentLevel = () => current;
/** Milliseconds per row for a well that has cleared `lines` rows so far. */
export function gravity(lines) {
    const base = (ladder.find((l) => l.key === current) ?? { gravity_ms: 280 }).gravity_ms;
    const stage = Math.floor(lines / 10);
    return Math.max(90, Math.round(base * Math.pow(0.86, stage)));
}
