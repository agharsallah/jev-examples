/* Pure formatting: numbers and names into the words the page shows. No DOM. */

import type { Cost, Probe, Severity, Verdict } from "./api.js";

export const VERDICT_CLASS: Record<Verdict, string> = {
  "SEND IT": "v-send",
  "TIGHTEN IT": "v-tighten",
  "REWRITE IT": "v-rewrite",
  "DO NOT SEND": "v-hold",
  UNREADABLE: "v-unclear",
};

export const GLYPH: Record<Severity, string> = {
  blocker: "!!", major: "!", minor: "·", good: "✓",
};

// The legend and tooltip wording. Not the same table as PROBE_LABELS in
// review/probes.py: the browser says "should not be here" for sensitive.
export const PROBE_LABEL: Record<Probe, string> = {
  carries_the_ask: "the ask",
  barbed: "reads as pointed",
  hedged: "hedging",
  ambiguous: "ambiguous",
  sensitive: "should not be here",
  cuttable: "could go",
};

export function verdictClass(verdict: string): string {
  return VERDICT_CLASS[verdict as Verdict] || "v-unclear";
}

export function probeLabel(name: string): string {
  return PROBE_LABEL[name as Probe] || name;
}

/** 0.873 -> "87%". */
export const pct = (value: number): string => `${Math.round(value * 100)}%`;

/** A position on the 0-4 scale as a CSS percentage along the track. */
export const onScale = (value: number): string => `${(value / 4) * 100}%`;

/** "spawns_a_meeting" -> "spawns a meeting". */
export const humanise = (name: string): string => name.replace(/_/g, " ");

export function costLine(cost: Cost, rescored: boolean): string {
  if (rescored) {
    return `re-scored in code · 0 requests to Jev · the measurements below are ` +
      `the same ones from the read above`;
  }
  const plural = cost.requests === 1 ? "request" : "requests";
  return `${cost.questions} questions in ${cost.requests} ${plural} · ` +
    `${cost.inputTokens} input tokens / ${cost.outputTokens} output`;
}
