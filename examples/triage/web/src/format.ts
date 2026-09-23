/* Numbers into words and marks. Nothing here invents a number. */

import { h } from "./dom.js";

export const pct = (p: number): string => `${Math.round(p * 100)}%`;
export const two = (p: number): string => p.toFixed(2);
export const dollars = (d: number): string => (d < 0.01 ? `$${d.toFixed(4)}` : `$${d.toFixed(3)}`);

/** One probability as a bar, with an optional threshold tick drawn on it. */
export function meter(p: number, opts: { threshold?: number; tone?: string; label?: string } = {}) {
  const width = Math.max(0, Math.min(1, p)) * 100;
  return h(
    "span",
    { class: `meter ${opts.tone ?? ""}`, role: "img", "aria-label": opts.label ?? pct(p) },
    h("span", { class: "fill", style: `width:${width}%` }),
    opts.threshold !== undefined
      ? h("span", { class: "tick", style: `left:${opts.threshold * 100}%`, title: `threshold ${two(opts.threshold)}` })
      : null,
  );
}

/** A distribution as ranked rows: label, bar, value. Top `limit` entries. */
export function distribution(
  probabilities: Record<string, number>,
  chosen: string,
  opts: { limit?: number; threshold?: number; names?: Record<string, string> } = {},
) {
  const rows = Object.entries(probabilities)
    .sort((a, b) => b[1] - a[1])
    .slice(0, opts.limit ?? 5)
    .filter(([, p], i) => i === 0 || p >= 0.005);
  return h(
    "div",
    { class: "dist" },
    rows.map(([name, p]) =>
      h(
        "div",
        { class: `dist-row${name === chosen ? " chosen" : ""}` },
        h("span", { class: "dist-name", title: name }, opts.names?.[name] ?? name),
        meter(p, { threshold: name === chosen ? opts.threshold : undefined }),
        h("span", { class: "dist-value" }, two(p)),
      ),
    ),
  );
}

export const KIND_TONE: Record<string, string> = {
  bug: "t-bug",
  feature: "t-feature",
  docs: "t-docs",
  question: "t-question",
  chore: "t-chore",
  other: "t-chore",
  neutral: "",
};

export const STATUS_WORD: Record<string, string> = {
  apply: "apply",
  confirm: "confirm",
  unsure: "unsure",
};
