/* Two small SVG charts and a heatmap, drawn by hand. Colours come from the
 * validated dark-surface slots (blue #3987e5, orange #d95926); text stays in
 * text tokens; every mark has a hover/focus readout, and every number is
 * also in the plain rows beside the chart. */

import { h } from "../dom.js";
import { pct, two } from "../format.js";

const NS = "http://www.w3.org/2000/svg";
const BLUE = "#3987e5";
const ORANGE = "#d95926";

function s<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number>, ...kids: (SVGElement | null)[]) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  for (const kid of kids) if (kid) el.append(kid);
  return el;
}

function text(x: number, y: number, value: string, attrs: Record<string, string | number> = {}) {
  const t = s("text", { x, y, class: "ax-text", ...attrs });
  t.textContent = value;
  return t;
}

interface Frame {
  svg: SVGSVGElement;
  x: (v: number) => number;
  y: (v: number) => number;
  tip: HTMLElement;
  wrap: HTMLElement;
}

/** A 0..1 × 0..1 plot with recessive gridlines and a shared tooltip. */
function frame(xLabel: string, yLabel: string): Frame {
  const W = 360, H = 230, L = 40, R = 58, T = 12, B = 34;
  const x = (v: number) => L + v * (W - L - R);
  const y = (v: number) => T + (1 - v) * (H - T - B);
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img" });
  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    svg.append(s("line", { x1: x(0), x2: x(1), y1: y(v), y2: y(v), class: "grid" }));
    svg.append(text(L - 6, y(v) + 4, pct(v), { "text-anchor": "end" }));
    svg.append(text(x(v), H - B + 16, two(v), { "text-anchor": "middle" }));
  }
  svg.append(text(x(0.5), H - 4, xLabel, { "text-anchor": "middle", class: "ax-title" }));
  svg.append(text(12, y(0.5), yLabel, { "text-anchor": "middle", class: "ax-title", transform: `rotate(-90 12 ${y(0.5)})` }));
  const tip = h("div", { class: "chart-tip", role: "status" });
  tip.hidden = true;
  const wrap = h("div", { class: "chart-wrap" });
  wrap.append(svg, tip);
  return { svg, x, y, tip, wrap };
}

function hover(f: Frame, target: SVGElement, cx: number, cy: number, lines: [string, string][]) {
  target.setAttribute("tabindex", "0");
  const show = () => {
    f.tip.replaceChildren(...lines.map(([value, label]) => h("div", null, h("strong", null, value), " ", h("span", null, label))));
    f.tip.style.left = `${(cx / 360) * 100}%`;
    f.tip.style.top = `${(cy / 230) * 100}%`;
    f.tip.hidden = false;
  };
  const hide = () => (f.tip.hidden = true);
  target.addEventListener("pointerenter", show);
  target.addEventListener("focus", show);
  target.addEventListener("pointerleave", hide);
  target.addEventListener("blur", hide);
}

export interface Bin { mean_p: number; accuracy: number; n: number; lo: number; hi: number }

/** Reliability: what Jev put on its pick, against how often the pick agreed.
 *  Dot area follows the bin's issue count; the diagonal is perfect calibration. */
export function reliabilityChart(bins: Bin[]) {
  const f = frame("probability Jev put on its pick", "agreed");
  f.svg.setAttribute("aria-label", "Calibration: predicted probability against observed agreement");
  f.svg.append(s("line", { x1: f.x(0), y1: f.y(0), x2: f.x(1), y2: f.y(1), class: "diagonal" }));
  // Dots only: a line through the bins would give a one-issue bin the same
  // visual weight as a ninety-issue one.
  const most = Math.max(1, ...bins.map((b) => b.n));
  for (const b of bins) {
    const cx = f.x(b.mean_p), cy = f.y(b.accuracy);
    const r = 4 + 6 * Math.sqrt(b.n / most);
    const g = s("g", { class: "hit" },
      s("circle", { cx, cy, r: Math.max(12, r + 4), fill: "transparent" }),
      s("circle", { cx, cy, r, fill: BLUE, stroke: "#131823", "stroke-width": 2 }),
    );
    hover(f, g, cx, cy, [[pct(b.accuracy), "agreed"], [two(b.mean_p), "mean probability"], [String(b.n), `issues (p ${two(b.lo)}–${two(b.hi)})`]]);
    f.svg.append(g);
  }
  return f.wrap;
}

export interface CoveragePoint { threshold: number; coverage: number; accuracy: number | null }

/** Raise the auto-apply bar: how many issues still clear it, and how often those agree. */
export function coverageChart(points: CoveragePoint[], marker?: number) {
  const f = frame("auto-apply when confidence ≥", "share of issues");
  f.svg.setAttribute("aria-label", "Coverage and agreement as the auto-apply threshold rises");
  const line = (key: "coverage" | "accuracy", color: string) => {
    const pts = points.filter((p) => p[key] !== null);
    const d = pts.map((p, i) => `${i ? "L" : "M"}${f.x(p.threshold)},${f.y(p[key] as number)}`).join(" ");
    f.svg.append(s("path", { d, fill: "none", stroke: color, "stroke-width": 2, "stroke-linejoin": "round" }));
    const last = pts[pts.length - 1];
    if (last) f.svg.append(text(f.x(last.threshold) + 8, f.y(last[key] as number) + 4, key === "coverage" ? "covered" : "agreed", { class: "ax-label" }));
  };
  line("coverage", ORANGE);
  line("accuracy", BLUE);
  if (marker !== undefined) {
    f.svg.append(s("line", { x1: f.x(marker), x2: f.x(marker), y1: f.y(0), y2: f.y(1), class: "marker-line" }));
  }
  // One hit column per threshold: the readout lists both series at that X.
  const step = (f.x(1) - f.x(0)) / Math.max(1, points.length);
  for (const p of points) {
    const cx = f.x(p.threshold);
    const g = s("g", { class: "hit" },
      s("rect", { x: cx - step / 2, y: f.y(1), width: step, height: f.y(0) - f.y(1), fill: "transparent" }),
      s("line", { x1: cx, x2: cx, y1: f.y(0), y2: f.y(1), class: "crosshair" }),
      s("circle", { cx, cy: f.y(p.coverage), r: 4, fill: ORANGE, class: "dot" }),
      p.accuracy !== null ? s("circle", { cx, cy: f.y(p.accuracy), r: 4, fill: BLUE, class: "dot" }) : null,
    );
    hover(f, g, cx, f.y(Math.max(p.coverage, p.accuracy ?? 0)), [
      [pct(p.coverage), "of issues auto-labelled"],
      [p.accuracy === null ? "—" : pct(p.accuracy), "of those agree"],
      [two(p.threshold), "threshold"],
    ]);
    f.svg.append(g);
  }
  const legend = h("div", { class: "chart-legend" },
    h("span", null, h("i", { style: `background:${ORANGE}` }), "covered"),
    h("span", null, h("i", { style: `background:${BLUE}` }), "agreed, among those covered"),
  );
  f.wrap.append(legend);
  return f.wrap;
}

/** Rows are the label on the issue, columns Jev's pick. One blue ramp, by row share. */
export function confusionTable(labels: string[], cells: number[][], names: Record<string, string> = {}) {
  const shown = labels.slice(0, 12);
  return h("div", { class: "confusion-wrap" },
    h("table", { class: "confusion" },
      h("thead", null, h("tr", null,
        h("th", { class: "corner" }, "on it ↓  Jev →"),
        shown.map((l) => h("th", { title: l }, h("span", null, names[l] ?? l))))),
      h("tbody", null, shown.map((truth, i) => {
        const row = cells[i] ?? [];
        const total = row.reduce((a, b) => a + b, 0) || 1;
        return h("tr", null,
          h("th", { title: truth }, names[truth] ?? truth),
          shown.map((pick, j) => {
            const n = row[j] ?? 0;
            const share = n / total;
            // Near zero recedes to the surface; the diagonal is where agreement lives.
            const bg = n ? `rgba(57,135,229,${(0.15 + share * 0.75).toFixed(2)})` : "transparent";
            return h("td", {
              class: `${i === j ? "diag" : ""}${share > 0.5 ? " strong" : ""}`,
              style: `background:${bg}`,
              title: `on it: ${truth} · Jev: ${pick} · ${n} of ${total} (${pct(share)})`,
              tabindex: n ? 0 : null,
            }, n ? String(n) : "");
          }));
      })),
    ),
  );
}
