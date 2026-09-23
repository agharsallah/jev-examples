/* Pure formatting: numbers and names into the words the page shows. No DOM. */
export const VERDICT_CLASS = {
    "SEND IT": "v-send",
    "TIGHTEN IT": "v-tighten",
    "REWRITE IT": "v-rewrite",
    "DO NOT SEND": "v-hold",
    UNREADABLE: "v-unclear",
};
export const GLYPH = {
    blocker: "!!", major: "!", minor: "·", good: "✓",
};
// The legend and tooltip wording. Not the same table as PROBE_LABELS in
// review/probes.py: the browser says "should not be here" for sensitive.
export const PROBE_LABEL = {
    carries_the_ask: "the ask",
    barbed: "reads as pointed",
    hedged: "hedging",
    ambiguous: "ambiguous",
    sensitive: "should not be here",
    cuttable: "could go",
};
export function verdictClass(verdict) {
    return VERDICT_CLASS[verdict] || "v-unclear";
}
export function probeLabel(name) {
    return PROBE_LABEL[name] || name;
}
/** 0.873 -> "87%". */
export const pct = (value) => `${Math.round(value * 100)}%`;
/** A position on the 0-4 scale as a CSS percentage along the track. */
export const onScale = (value) => `${(value / 4) * 100}%`;
/** "spawns_a_meeting" -> "spawns a meeting". */
export const humanise = (name) => name.replace(/_/g, " ");
export function costLine(cost, rescored) {
    if (rescored) {
        return `re-scored in code · 0 requests to Jev · the measurements below are ` +
            `the same ones from the read above`;
    }
    const plural = cost.requests === 1 ? "request" : "requests";
    return `${cost.questions} questions in ${cost.requests} ${plural} · ` +
        `${cost.inputTokens} input tokens / ${cost.outputTokens} output`;
}
