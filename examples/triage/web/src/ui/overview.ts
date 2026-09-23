/* The whole backlog: every open issue, read once, and laid out so a
 * maintainer or product owner can see the shape of it — what is ready, what a
 * newcomer could take, what is waiting on a decision, which issues are the
 * same problem twice — and click through to any one of them.
 *
 * Everything on this page is computed in the browser from the rows the
 * server sent: the flags are thresholds (the knobs), the clusters are
 * union-find over the pairwise duplicate answers, and the filters narrow
 * every view at once. Nothing here asks Jev anything. */

import type { Overview, OverviewEdge, OverviewRow } from "../api.js";
import { h } from "../dom.js";
import { dollars, githubLink, meter, pct, two } from "../format.js";

// Validated dark-surface categorical slots, in fixed order, one per kind.
export const KIND_COLOR: Record<string, string> = {
  feature: "#3987e5",
  bug: "#d95926",
  docs: "#199e70",
  question: "#c98500",
  chore: "#d55181",
  other: "#8b95ab",
};
const KINDS = Object.keys(KIND_COLOR);

export interface Knobs {
  readyAt: number;
  beginnerAt: number;
  dupAt: number;
}

export type Flag = "ready" | "beginner" | "decision" | "ask" | "duplicate" | "security" | "close" | "drift";
export type Quadrant = "next" | "unblock" | "quick" | "backlog";

export interface Filters {
  flag: Flag | null;
  kind: string | null;
  component: string | null;
  quadrant: Quadrant | null;
  q: string;
}

export interface OverviewHooks {
  open: (n: number) => void;
  filter: (patch: Partial<Filters>) => void;
  knobs: (patch: Partial<Knobs>) => void;
  sort: (key: SortKey) => void;
}

export type SortKey = "readiness" | "beginner" | "impact" | "priority" | "age_days" | "number";

const BLOCKED = new Set(["private", "human", "needs_info", "duplicate", "close"]);
const IMPACT_LINE = 0.5;

// -- the definitions: every flag in one place -----------------------------

export function flags(row: OverviewRow, k: Knobs, dupes: Set<number>): Set<Flag> {
  const out = new Set<Flag>();
  const decided = row.needs_decision < 0.5;
  if (row.readiness >= k.readyAt && decided && !BLOCKED.has(row.lane)) out.add("ready");
  if (row.beginner >= k.beginnerAt && decided && row.security < 0.5 && !["private", "close", "duplicate"].includes(row.lane)) out.add("beginner");
  if (row.needs_decision >= 0.6) out.add("decision");
  if (row.lanes.includes("needs_info")) out.add("ask");
  if (dupes.has(row.number)) out.add("duplicate");
  if (row.lanes.includes("private")) out.add("security");
  if (row.lanes.includes("close")) out.add("close");
  if (row.drift.length) out.add("drift");
  return out;
}

export function quadrant(row: OverviewRow, k: Knobs): Quadrant {
  const ready = row.readiness >= k.readyAt;
  const big = row.impact >= IMPACT_LINE;
  return big ? (ready ? "next" : "unblock") : ready ? "quick" : "backlog";
}

const FLAG_WORDS: Record<Flag, [string, string]> = {
  ready: ["Ready to pick up", "clear, decided, actionable — and nothing blocks it"],
  beginner: ["Good first issues", "small, clear, and needs little project knowledge"],
  decision: ["Waiting on a decision", "what to build is still an open question"],
  ask: ["Ask the reporter", "a bug missing the essentials to reproduce it"],
  duplicate: ["In a duplicate cluster", "the same problem, filed more than once"],
  security: ["Handle privately", "may describe a vulnerability or leak a secret"],
  close: ["Close candidates", "reported fixed, answered, or spam"],
  drift: ["Label drift", "a label on it disagrees with what Jev reads"],
};

const QUADRANT_WORDS: Record<Quadrant, [string, string]> = {
  next: ["Do next", "high impact, ready to work on"],
  unblock: ["Unblock first", "high impact, not ready: needs info or a decision"],
  quick: ["Quick wins", "lower impact, ready: good for contributors"],
  backlog: ["Backlog", "lower impact, not ready"],
};

// -- duplicates: union-find over 'same problem' answers --------------------

export interface Cluster {
  members: number[];
  edges: OverviewEdge[];
  titles: Map<number, { title: string; state: string; url: string; open: boolean }>;
}

export function clusters(data: Overview, dupAt: number): Cluster[] {
  const parent = new Map<number, number>();
  const find = (x: number): number => {
    let root = x;
    while (parent.get(root) !== undefined && parent.get(root) !== root) root = parent.get(root)!;
    parent.set(x, root);
    return root;
  };
  const strong = data.edges.filter((e) => e.same >= dupAt);
  for (const e of strong) {
    if (!parent.has(e.a)) parent.set(e.a, e.a);
    if (!parent.has(e.b)) parent.set(e.b, e.b);
    parent.set(find(e.a), find(e.b));
  }
  const open = new Map(data.rows.map((r) => [r.number, r]));
  const groups = new Map<number, Cluster>();
  for (const e of strong) {
    const root = find(e.a);
    const c: Cluster = groups.get(root) ?? { members: [], edges: [], titles: new Map() };
    c.edges.push(e);
    for (const [n, title, state, url] of [
      [e.a, open.get(e.a)?.title ?? "", "open", open.get(e.a)?.url ?? ""],
      [e.b, e.b_title, e.b_state, e.b_url],
    ] as [number, string, string, string][]) {
      if (!c.titles.has(n)) {
        c.members.push(n);
        c.titles.set(n, { title, state, url, open: open.has(n) });
      }
    }
    groups.set(root, c);
  }
  // Two issues can each name the other; keep the stronger answer per pair.
  for (const c of groups.values()) {
    const best = new Map<string, OverviewEdge>();
    for (const e of c.edges) {
      const key = [e.a, e.b].sort((x, y) => x - y).join("-");
      if (!best.has(key) || best.get(key)!.same < e.same) best.set(key, e);
    }
    c.edges = [...best.values()].sort((x, y) => y.same - x.same);
    c.members.sort((x, y) => x - y);
  }
  return [...groups.values()].sort((x, y) => y.members.length - x.members.length || y.edges[0]!.same - x.edges[0]!.same);
}

// -- the page -------------------------------------------------------------

export function overviewView(
  data: Overview,
  k: Knobs,
  f: Filters,
  sort: SortKey,
  hooks: OverviewHooks,
) {
  const groups = clusters(data, k.dupAt);
  const inCluster = new Set(groups.flatMap((c) => c.members));
  const flagged = new Map(data.rows.map((r) => [r.number, flags(r, k, inCluster)]));
  const q = f.q.trim().toLowerCase();
  const visible = data.rows.filter((r) =>
    (!f.flag || flagged.get(r.number)!.has(f.flag)) &&
    (!f.kind || r.kind === f.kind) &&
    (!f.component || (r.component ?? "(none fits)") === f.component) &&
    (!f.quadrant || quadrant(r, k) === f.quadrant) &&
    (!q || r.title.toLowerCase().includes(q) || String(r.number) === q.replace("#", "")),
  );
  const shown = new Set(visible.map((r) => r.number));

  return h("div", { class: "overview" },
    tiles(data, flagged, groups, f, hooks),
    filterBar(f, visible.length, data.rows.length, hooks),
    h("div", { class: "ov-grid" },
      h("section", { class: "card ov-map" },
        head("The map", "impact against readiness · one dot per issue · click one to open it"),
        mapChart(data.rows, shown, k, f, hooks),
        kindLegend("click a quadrant to filter"),
      ),
      h("section", { class: "card" },
        head("Where the work is", "Jev's component pick × kind · click a bar to filter"),
        breakdownChart(visible, f, hooks),
        kindLegend("a segment filters to that component and kind"),
      ),
    ),
    shortlists(visible, flagged, hooks),
    duplicatesPanel(groups, shown, f, hooks),
    explorer(visible, flagged, sort, hooks),
    knobsCard(data, k, hooks),
  );
}

function head(title: string, note: string) {
  return h("header", { class: "card-head" }, h("h3", null, title), h("span", { class: "card-note" }, note));
}

// -- tiles ----------------------------------------------------------------

function tiles(data: Overview, flagged: Map<number, Set<Flag>>, groups: Cluster[], f: Filters, hooks: OverviewHooks) {
  const count = (flag: Flag) => [...flagged.values()].filter((s) => s.has(flag)).length;
  const t = data.totals;
  const tile = (flag: Flag, value: string, extra?: string) =>
    h("button", {
      class: `tile tile-${flag}${f.flag === flag ? " active" : ""}`,
      type: "button",
      title: FLAG_WORDS[flag][1],
      "aria-pressed": f.flag === flag ? "true" : "false",
      onclick: () => hooks.filter({ flag: f.flag === flag ? null : flag }),
    }, h("strong", null, value), h("span", null, FLAG_WORDS[flag][0]), extra ? h("small", null, extra) : null);
  return h("div", { class: "tiles" },
    h("div", { class: "tile static" },
      h("strong", null, String(data.repo.read)),
      h("span", null, "open issues read"),
      h("small", null, `${t.questions.toLocaleString()} questions · ${dollars(t.cost_usd)}${data.repo.read < data.repo.open_issues ? ` · newest ${data.repo.read} of ${data.repo.open_issues}` : ""}`),
    ),
    tile("ready", String(count("ready"))),
    tile("beginner", String(count("beginner"))),
    tile("decision", String(count("decision"))),
    tile("ask", String(count("ask"))),
    tile("duplicate", String(count("duplicate")), `${groups.length} cluster${groups.length === 1 ? "" : "s"}`),
    tile("security", String(count("security"))),
    tile("close", String(count("close"))),
    tile("drift", String(count("drift"))),
  );
}

function filterBar(f: Filters, shown: number, total: number, hooks: OverviewHooks) {
  const chips: Node[] = [];
  const chip = (text: string, clear: Partial<Filters>) =>
    chips.push(h("button", { class: "chip filter", type: "button", onclick: () => hooks.filter(clear) }, text, h("i", null, "×")));
  if (f.flag) chip(FLAG_WORDS[f.flag][0], { flag: null });
  if (f.quadrant) chip(QUADRANT_WORDS[f.quadrant][0], { quadrant: null });
  if (f.kind) chip(`kind: ${f.kind}`, { kind: null });
  if (f.component) chip(`component: ${f.component}`, { component: null });
  const search = h("input", { type: "search", placeholder: "filter by title or #number", value: f.q, "aria-label": "filter issues" });
  search.addEventListener("input", () => hooks.filter({ q: search.value }));
  return h("div", { class: "filter-bar" },
    search,
    h("div", { class: "chips" }, chips),
    h("span", { class: "faint small" }, shown === total ? `all ${total} issues` : `${shown} of ${total} issues`),
    chips.length ? h("button", { class: "ghost small", type: "button", onclick: () => hooks.filter({ flag: null, kind: null, component: null, quadrant: null, q: "" }) }, "clear filters") : null,
  );
}

// -- the map --------------------------------------------------------------

const NS = "http://www.w3.org/2000/svg";
function s<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number>, ...kids: (SVGElement | null)[]) {
  const el = document.createElementNS(NS, tag);
  for (const [key, v] of Object.entries(attrs)) el.setAttribute(key, String(v));
  for (const kid of kids) if (kid) el.append(kid);
  return el;
}
function label(x: number, y: number, text: string, attrs: Record<string, string | number> = {}) {
  const t = s("text", { x, y, class: "ax-text", ...attrs });
  t.textContent = text;
  return t;
}

function mapChart(rows: OverviewRow[], shown: Set<number>, k: Knobs, f: Filters, hooks: OverviewHooks) {
  const W = 560, H = 360, L = 44, R = 14, T = 14, B = 40;
  // Readiness rarely falls below ~0.3; start the axis just under the data so
  // the dots use the width. Impact keeps its full 0..1 range.
  const lo = Math.max(0, Math.min(k.readyAt - 0.1, Math.floor(Math.min(...rows.map((r) => r.readiness)) * 10) / 10));
  const x = (v: number) => L + ((v - lo) / (1 - lo)) * (W - L - R);
  const y = (v: number) => T + (1 - v) * (H - T - B);
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart map", role: "img", "aria-label": "Every open issue by readiness and impact" });

  // Quadrants: shaded when selected, clickable to filter.
  const quads: [Quadrant, number, number, number, number][] = [
    ["unblock", lo, IMPACT_LINE, k.readyAt, 1],
    ["next", k.readyAt, IMPACT_LINE, 1, 1],
    ["backlog", lo, 0, k.readyAt, IMPACT_LINE],
    ["quick", k.readyAt, 0, 1, IMPACT_LINE],
  ];
  for (const [name, x0, y0, x1, y1] of quads) {
    const rect = s("rect", {
      x: x(x0), y: y(y1), width: x(x1) - x(x0), height: y(y0) - y(y1),
      class: `quad${f.quadrant === name ? " active" : ""}`,
    });
    rect.addEventListener("click", () => hooks.filter({ quadrant: f.quadrant === name ? null : name }));
    svg.append(rect);
  }
  const quadLabels = quads.map(([name, x0, y0, x1, y1]) => {
    const tx = name === "next" || name === "quick" ? x(x1) - 8 : x(x0) + 8;
    const anchor = name === "next" || name === "quick" ? "end" : "start";
    const ty = name === "next" || name === "unblock" ? y(y1) + 16 : y(y0) - 8;
    return label(tx, ty, QUADRANT_WORDS[name][0], { "text-anchor": anchor, class: "quad-label" });
  });
  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    svg.append(label(L - 6, y(v) + 4, two(v), { "text-anchor": "end" }));
  }
  for (let v = Math.ceil(lo * 10) / 10; v <= 1.0001; v += 0.1) {
    svg.append(label(x(v), H - B + 16, v.toFixed(1), { "text-anchor": "middle" }));
  }
  svg.append(s("line", { x1: x(k.readyAt), x2: x(k.readyAt), y1: y(0), y2: y(1), class: "marker-line" }));
  svg.append(s("line", { x1: x(lo), x2: x(1), y1: y(IMPACT_LINE), y2: y(IMPACT_LINE), class: "marker-line" }));
  svg.append(label(x(0.5), H - 6, "readiness → (clear, decided, actionable)", { "text-anchor": "middle", class: "ax-title" }));
  svg.append(label(12, y(0.5), "impact →", { "text-anchor": "middle", class: "ax-title", transform: `rotate(-90 12 ${y(0.5)})` }));

  const tip = h("div", { class: "chart-tip", role: "status" });
  tip.hidden = true;
  // Dim first, bright on top, so a filter reads as a spotlight.
  const ordered = [...rows].sort((a, b) => Number(shown.has(a.number)) - Number(shown.has(b.number)));
  for (const r of ordered) {
    const on = shown.has(r.number);
    const cx = x(r.readiness), cy = y(r.impact);
    const g = s("g", { class: `pt${on ? "" : " dim"}`, tabindex: on ? 0 : -1 },
      s("circle", { cx, cy, r: 10, fill: "transparent" }),
      s("circle", { cx, cy, r: 4.5, fill: KIND_COLOR[r.kind] ?? KIND_COLOR.other!, stroke: "#131823", "stroke-width": 1.5 }),
    );
    const show = () => {
      tip.replaceChildren(
        h("div", null, h("strong", null, `#${r.number}`), " ", h("span", null, r.title.length > 70 ? `${r.title.slice(0, 70)}…` : r.title)),
        h("div", null, h("strong", null, two(r.readiness)), h("span", null, " readiness · "), h("strong", null, two(r.impact)), h("span", null, ` impact · ${r.kind}`)),
      );
      tip.style.left = `${(cx / W) * 100}%`;
      tip.style.top = `${(cy / H) * 100}%`;
      tip.hidden = false;
    };
    g.addEventListener("pointerenter", show);
    g.addEventListener("focus", show);
    g.addEventListener("pointerleave", () => (tip.hidden = true));
    g.addEventListener("blur", () => (tip.hidden = true));
    g.addEventListener("click", () => hooks.open(r.number));
    g.addEventListener("keydown", (e) => { if ((e as KeyboardEvent).key === "Enter") hooks.open(r.number); });
    svg.append(g);
  }
  for (const text of quadLabels) svg.append(text);
  const wrap = h("div", { class: "chart-wrap map-wrap" });
  wrap.append(svg, tip);
  return wrap;
}

function kindLegend(note: string) {
  return h("div", { class: "chart-legend" },
    KINDS.map((kind) => h("span", null, h("b", { class: "dot-key", style: `background:${KIND_COLOR[kind]}` }), kind)),
    h("span", { class: "faint" }, `· ${note}`),
  );
}

// -- breakdown: component × kind stacked bars --------------------------------

function breakdownChart(rows: OverviewRow[], f: Filters, hooks: OverviewHooks) {
  const by = new Map<string, Map<string, number>>();
  for (const r of rows) {
    const comp = r.component ?? "(none fits)";
    const m = by.get(comp) ?? new Map();
    m.set(r.kind, (m.get(r.kind) ?? 0) + 1);
    by.set(comp, m);
  }
  const bars = [...by.entries()]
    .map(([comp, kinds]) => ({ comp, kinds, total: [...kinds.values()].reduce((a, b) => a + b, 0) }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 14);
  const most = Math.max(1, ...bars.map((b) => b.total));
  if (!bars.length) return h("p", { class: "faint" }, "Nothing matches the filters.");
  return h("div", { class: "bars" },
    bars.map((b) =>
      h("div", { class: `bar-row${f.component === b.comp ? " active" : ""}` },
        h("button", { class: "bar-name link", type: "button", title: b.comp, onclick: () => hooks.filter({ component: f.component === b.comp ? null : b.comp }) }, b.comp),
        h("div", { class: "bar-track" },
          h("div", { class: "bar-stack", style: `width:${(b.total / most) * 100}%` },
            KINDS.filter((kind) => b.kinds.get(kind)).map((kind) =>
              h("button", {
                class: "seg",
                type: "button",
                style: `flex:${b.kinds.get(kind)};background:${KIND_COLOR[kind]}`,
                title: `${b.comp} · ${kind}: ${b.kinds.get(kind)}`,
                "aria-label": `${b.comp}, ${kind}: ${b.kinds.get(kind)}`,
                onclick: () => hooks.filter({ component: b.comp, kind }),
              }),
            ),
          ),
        ),
        h("span", { class: "dist-value" }, String(b.total)),
      ),
    ),
  );
}

// -- shortlists -------------------------------------------------------------

function shortlists(rows: OverviewRow[], flagged: Map<number, Set<Flag>>, hooks: OverviewHooks) {
  const list = (flag: Flag, score: (r: OverviewRow) => number, metric: string, why: (r: OverviewRow) => string) => {
    const items = rows.filter((r) => flagged.get(r.number)!.has(flag)).sort((a, b) => score(b) - score(a));
    return h("section", { class: `card shortlist sl-${flag}` },
      h("header", { class: "card-head" },
        h("h3", null, FLAG_WORDS[flag][0]),
        h("button", { class: "ghost small", type: "button", onclick: () => hooks.filter({ flag }) }, `all ${items.length}`),
      ),
      h("p", { class: "faint small" }, FLAG_WORDS[flag][1], ` · ranked by ${metric}`),
      items.length
        ? h("ol", null, items.slice(0, 8).map((r) =>
            h("li", { class: "sl-row" },
              h("button", { class: "sl-item", type: "button", onclick: () => hooks.open(r.number) },
                h("span", { class: "num" }, `#${r.number}`),
                h("span", { class: "sl-title" }, r.title),
                h("span", { class: "sl-score" }, meter(score(r), { tone: "t-lamp" }), h("b", null, two(score(r)))),
                h("small", { class: "faint" }, why(r)),
              ),
              githubLink(r.url, "↗"),
            )))
        : h("p", { class: "faint" }, "None right now."),
    );
  };
  return h("div", { class: "shortlists" },
    list("ready", (r) => r.readiness * (0.6 + 0.4 * r.impact), "readiness × impact",
      (r) => `${r.kind}${r.component ? ` · ${r.component}` : ""} · impact ${two(r.impact)}`),
    list("beginner", (r) => r.beginner, "beginner score",
      (r) => `scope ${two(r.scope)}${r.beginner_label && r.beginner_label_p !== null ? ` · ‘${r.beginner_label}’ ${two(r.beginner_label_p)}` : ""}`),
    list("decision", (r) => r.needs_decision * (0.5 + 0.5 * r.impact), "open question × impact",
      (r) => `${r.kind} · impact ${two(r.impact)} · ${r.comments} comments`),
    list("ask", (r) => r.impact, "impact",
      (r) => `missing ${r.missing.map((m) => m.slice(4).replace(/_/g, " ")).join(", ") || "details"}`),
  );
}

// -- duplicates -------------------------------------------------------------

function duplicatesPanel(groups: Cluster[], shown: Set<number>, f: Filters, hooks: OverviewHooks) {
  const visible = f.flag || f.kind || f.component || f.quadrant || f.q
    ? groups.filter((c) => c.members.some((n) => shown.has(n)))
    : groups;
  return h("section", { class: "card" },
    head("Duplicate clusters", "issues Jev reads as the same underlying problem · linked by ‘same problem’ probability"),
    visible.length
      ? h("div", { class: "clusters" }, visible.slice(0, 24).map((c) => clusterCard(c, hooks)))
      : h("p", { class: "faint" }, "No pair clears the duplicate threshold. Lower it in the knobs to see near-misses."),
  );
}

function clusterCard(c: Cluster, hooks: OverviewHooks) {
  // The oldest member is the one to keep; the rest point at it.
  const keep = c.members[0]!;
  const closed = c.members.filter((n) => !c.titles.get(n)!.open);
  return h("div", { class: "cluster" },
    clusterGraph(c),
    closed.length
      ? h("p", { class: "cl-hint" }, `#${closed.join(", #")} is already closed — check whether the open ${c.members.length - closed.length > 1 ? "ones are" : "one is"} fixed too.`)
      : h("p", { class: "cl-hint" }, `All open: keep #${keep}, close the other${c.members.length > 2 ? "s" : ""} as duplicate${c.members.length > 2 ? "s" : ""}.`),
    h("ul", null, c.members.map((n) => {
      const m = c.titles.get(n)!;
      return h("li", null,
        m.open
          ? h("button", { class: "link", type: "button", title: "Open the triage", onclick: () => hooks.open(n) }, `#${n}`)
          : h("span", { class: "num" }, `#${n}`),
        " ",
        h("span", { class: `state s-${m.state}` }, m.state),
        n === keep ? h("span", { class: "keep" }, "oldest") : null,
        " ", h("span", { class: "cl-title" }, m.title),
        m.url ? [" ", githubLink(m.url, "↗")] : null,
      );
    })),
    h("div", { class: "cl-edges" }, c.edges.map((e) =>
      h("span", { class: "move" }, `#${e.a} ⇄ #${e.b} `, h("b", null, two(e.same))))),
  );
}

function clusterGraph(c: Cluster) {
  const n = c.members.length;
  const W = 180, H = n === 2 ? 40 : 110, R = 38, cx = W / 2, cy = H / 2;
  const pos = new Map(c.members.map((m, i) => {
    const angle = n === 2 ? Math.PI * i : (2 * Math.PI * i) / n - Math.PI / 2;
    return [m, [cx + (n === 2 ? 55 : R) * Math.cos(angle), cy + (n === 2 ? 0 : R) * Math.sin(angle)]] as const;
  }));
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "cl-graph", role: "img", "aria-label": `cluster of ${n} issues` });
  for (const e of c.edges) {
    const [x1, y1] = pos.get(e.a)!, [x2, y2] = pos.get(e.b)!;
    svg.append(s("line", { x1, y1, x2, y2, stroke: "#3987e5", "stroke-width": 1 + 4 * e.same, opacity: 0.35 + 0.6 * e.same }));
  }
  for (const m of c.members) {
    const [x, y] = pos.get(m)!;
    const open = c.titles.get(m)!.open;
    svg.append(s("circle", { cx: x, cy: y, r: 13, class: open ? "node open" : "node closed" }));
    svg.append(label(x, y + 4, `${m}`, { "text-anchor": "middle", class: "node-label" }));
  }
  return svg;
}

// -- the explorer table -----------------------------------------------------

const FLAG_ICON: Partial<Record<Flag, string>> = {
  ready: "ready", beginner: "first", decision: "decide", ask: "ask", duplicate: "dup", security: "private", close: "close", drift: "drift",
};

function explorer(rows: OverviewRow[], flagged: Map<number, Set<Flag>>, sort: SortKey, hooks: OverviewHooks) {
  const sorted = [...rows].sort((a, b) =>
    sort === "number" ? b.number - a.number
    : sort === "age_days" ? (b.age_days ?? 0) - (a.age_days ?? 0)
    : (b[sort] as number) - (a[sort] as number));
  const col = (key: SortKey, text: string) =>
    h("th", { class: `sortable${sort === key ? " sorted" : ""}`, onclick: () => hooks.sort(key), "aria-sort": sort === key ? "descending" : "none" }, text);
  const bar = (v: number) => h("td", { class: "num" }, h("span", { class: "mini" }, meter(v, { tone: "t-lamp" })), two(v));
  return h("section", { class: "card" },
    head("Every issue", `${rows.length} shown · click a row for the full triage · click a column to sort`),
    h("div", { class: "table-wrap" },
      h("table", { class: "explorer" },
        h("thead", null, h("tr", null,
          col("number", "#"), h("th", null, "title"), h("th", { "aria-label": "GitHub" }, ""), h("th", null, "kind"), h("th", null, "component"),
          col("readiness", "ready"), col("beginner", "beginner"), col("impact", "impact"), col("priority", "priority"),
          col("age_days", "age"), h("th", null, "flags"))),
        h("tbody", null, sorted.slice(0, 200).map((r) =>
          h("tr", { tabindex: 0, onclick: () => hooks.open(r.number), onkeydown: (e: Event) => { if ((e as KeyboardEvent).key === "Enter") hooks.open(r.number); } },
            h("td", { class: "num" }, `#${r.number}`),
            h("td", { class: "t-title", title: r.title }, r.title),
            h("td", null, githubLink(r.url, "↗")),
            h("td", null, h("span", { class: "kind-dot", style: `background:${KIND_COLOR[r.kind] ?? KIND_COLOR.other}` }), r.kind),
            h("td", { class: "faint" }, r.component ?? "—"),
            bar(r.readiness), bar(r.beginner), bar(r.impact), bar(r.priority),
            h("td", { class: "num faint" }, r.age_days === null ? "—" : `${r.age_days}d`),
            h("td", null, [...flagged.get(r.number)!].map((fl) => h("span", { class: `flag fl-${fl}` }, FLAG_ICON[fl] ?? fl))),
          ))),
      ),
    ),
    rows.length > 200 ? h("p", { class: "faint small" }, `Showing the first 200 of ${rows.length}. Narrow with the filters above.`) : null,
  );
}

// -- knobs and definitions --------------------------------------------------

function knobsCard(data: Overview, k: Knobs, hooks: OverviewHooks) {
  const slider = (key: keyof Knobs, text: string) => {
    const out = h("output", null, two(k[key]));
    const input = h("input", { type: "range", min: 0.3, max: 0.99, step: 0.01, value: k[key], "aria-label": text });
    input.addEventListener("change", () => hooks.knobs({ [key]: Number(input.value) }));
    input.addEventListener("input", () => (out.textContent = two(Number(input.value))));
    return h("label", { class: "knob" }, h("span", null, text), input, out);
  };
  const weights = (w: Record<string, number>) =>
    Object.entries(w).map(([name, v]) => `${pct(v)} ${name}`).join(" + ");
  return h("section", { class: "card" },
    head("How these are computed", "plain code over Jev's answers · the knobs recompute in the browser"),
    slider("readyAt", "ready to pick up at readiness ≥"),
    slider("beginnerAt", "good first issue at beginner ≥"),
    slider("dupAt", "duplicates when ‘same problem’ ≥"),
    h("dl", { class: "defs" },
      h("dt", null, "readiness"), h("dd", null, weights(data.weights.readiness), ". ‘decided’ is 1 − needs a decision; ‘reproducible’ counts only for bugs."),
      h("dt", null, "beginner"), h("dd", null, weights(data.weights.beginner), ". ‘small’ is 1 − scope."),
      h("dt", null, "impact"), h("dd", null, "Jev's impact Score, 0 (cosmetic) to 1 (data loss or unusable)."),
      h("dt", null, "ready to pick up"), h("dd", null, "readiness over the bar, no open decision, and not in a private, human, ask-the-reporter, duplicate or close lane."),
    ),
  );
}
