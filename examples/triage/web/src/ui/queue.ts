/* The queue: every recent open issue, read once, sorted into lanes by the
 * policy. The knobs beside it rescore the whole queue from the same answers. */

import type { QueueRow, ScanResult } from "../api.js";
import { h } from "../dom.js";
import { dollars, githubLink, meter, two } from "../format.js";

const LANE_ORDER = ["private", "human", "needs_info", "duplicate", "close", "confirm", "auto"];

export function queueBoard(scan: ScanResult, rows: QueueRow[], lanes: Record<string, string>, onOpen: (n: number) => void) {
  const byLane = new Map<string, QueueRow[]>();
  for (const row of rows) {
    const lane = row.assessment.lane;
    byLane.set(lane, [...(byLane.get(lane) ?? []), row]);
  }
  const t = scan.totals;
  const drift = rows.filter((r) => r.assessment.drift.length).length;
  const dups = rows.filter((r) => r.assessment.duplicates[0]?.verdict === "duplicate").length;
  return h("div", { class: "queue" },
    h("div", { class: "queue-stats" },
      stat(String(rows.length), "open issues read"),
      stat(String(t.questions.toLocaleString()), "questions asked"),
      stat(dollars(t.cost_usd), `${t.input_tokens.toLocaleString()} tokens`),
      stat(`${t.mean_latency_s.toFixed(2)}s`, "per issue"),
      stat(String(drift), "with label drift"),
      stat(String(dups), "likely duplicates"),
    ),
    t.skipped.length
      ? h("p", { class: "faint small" }, `${t.skipped.length} refused by the API's firewall: `, t.skipped.map((s) => `#${s.number}`).join(", "))
      : null,
    h("div", { class: "lanes-board" },
      LANE_ORDER.filter((lane) => byLane.has(lane)).map((lane) => {
        const items = (byLane.get(lane) ?? []).sort((a, b) => b.assessment.priority - a.assessment.priority);
        return h("section", { class: `lane-col lane-col-${lane}` },
          h("header", null, h("span", { class: `lane lane-${lane}` }, lanes[lane] ?? lane), h("span", { class: "faint" }, String(items.length))),
          items.map((row) => queueCard(row, onOpen)),
        );
      }),
    ),
  );
}

function stat(value: string, label: string) {
  return h("div", { class: "stat" }, h("strong", null, value), h("span", null, label));
}

function queueCard(row: QueueRow, onOpen: (n: number) => void) {
  const a = row.assessment;
  const onIt = new Set(row.labels);
  const add = a.labels.filter((l) => l.status !== "unsure" && !onIt.has(l.label));
  const dup = a.duplicates[0];
  return h("div", { class: "qcard-wrap" }, h("button", { class: "qcard", type: "button", onclick: () => onOpen(row.number) },
    h("div", { class: "qcard-head" },
      h("span", { class: "num" }, `#${row.number}`),
      h("span", { class: `kind t-${row.kind}` }, row.kind, h("small", null, two(row.kind_confidence))),
    ),
    h("div", { class: "qcard-title" }, row.title),
    h("div", { class: "qcard-priority" }, meter(a.priority, { tone: "t-lamp" }), h("span", { class: "dist-value" }, two(a.priority))),
    add.length ? h("div", { class: "chips small" }, add.slice(0, 4).map((l) => h("span", { class: `chip s-${l.status}` }, l.label))) : null,
    a.drift.length ? h("div", { class: "qcard-note" }, `drift: ${a.drift[0]!.current} → ${a.drift[0]!.suggested}`) : null,
    dup && dup.verdict !== "unrelated" ? h("div", { class: "qcard-note" }, `${dup.verdict}: #${dup.number} (${two(dup.same)})`) : null,
    a.missing.length ? h("div", { class: "qcard-note" }, `missing: ${a.missing.map((m) => m.slice(4).replace(/_/g, " ")).join(", ")}`) : null,
  ), githubLink(row.url));
}
