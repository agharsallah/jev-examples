/* Numbers into words and marks. Nothing here invents a number. */
import { h } from "./dom.js";
export const pct = (p) => `${Math.round(p * 100)}%`;
export const two = (p) => p.toFixed(2);
export const dollars = (d) => (d < 0.01 ? `$${d.toFixed(4)}` : `$${d.toFixed(3)}`);
/** One probability as a bar, with an optional threshold tick drawn on it. */
export function meter(p, opts = {}) {
    const width = Math.max(0, Math.min(1, p)) * 100;
    return h("span", { class: `meter ${opts.tone ?? ""}`, role: "img", "aria-label": opts.label ?? pct(p) }, h("span", { class: "fill", style: `width:${width}%` }), opts.threshold !== undefined
        ? h("span", { class: "tick", style: `left:${opts.threshold * 100}%`, title: `threshold ${two(opts.threshold)}` })
        : null);
}
/** A distribution as ranked rows: label, bar, value. Top `limit` entries. */
export function distribution(probabilities, chosen, opts = {}) {
    const rows = Object.entries(probabilities)
        .sort((a, b) => b[1] - a[1])
        .slice(0, opts.limit ?? 5)
        .filter(([, p], i) => i === 0 || p >= 0.005);
    return h("div", { class: "dist" }, rows.map(([name, p]) => h("div", { class: `dist-row${name === chosen ? " chosen" : ""}` }, h("span", { class: "dist-name", title: name }, opts.names?.[name] ?? name), meter(p, { threshold: name === chosen ? opts.threshold : undefined }), h("span", { class: "dist-value" }, two(p)))));
}
export const KIND_TONE = {
    bug: "t-bug",
    feature: "t-feature",
    docs: "t-docs",
    question: "t-question",
    chore: "t-chore",
    other: "t-chore",
    neutral: "",
};
export const STATUS_WORD = {
    apply: "apply",
    confirm: "confirm",
    unsure: "unsure",
};
/** The issue on GitHub, in a new tab. Stops the click from also opening the
 * in-app triage when it sits inside a clickable row. */
export function githubLink(url, text = "GitHub ↗") {
    const a = h("a", { class: "gh-link", href: url, target: "_blank", rel: "noopener", title: "Open on GitHub" }, text);
    a.addEventListener("click", (e) => e.stopPropagation());
    a.addEventListener("keydown", (e) => e.stopPropagation());
    return a;
}
