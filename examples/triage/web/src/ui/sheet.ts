/* The issue as paper: its own text, with each unit Jev was asked about marked
 * by what that unit signalled. Click a unit to see its distribution, and to
 * take it out and ask again. */

import type { Assessment, ChoiceAnswer, Measurement, Unit } from "../api.js";
import { fill, h } from "../dom.js";
import { KIND_TONE, distribution, two } from "../format.js";

export type Lens = "kind" | "comp" | "off";

export interface SheetHooks {
  onRemove: (units: number[]) => void;
}

function unitAnswer(m: Measurement, unit: Unit, lens: Lens): ChoiceAnswer | null {
  if (lens === "off") return null;
  const answer = m.answers[`u${unit.index}__${lens}`];
  return answer && answer.type === "choice" ? answer : null;
}

/** How strongly a unit is painted, and in what colour, under the current lens. */
function paint(m: Measurement, a: Assessment, unit: Unit, lens: Lens): { cls: string; alpha: number; tip: string } | null {
  const answer = unitAnswer(m, unit, lens);
  if (!answer) return null;
  const signal = answer.choice;
  const p = answer.probabilities[signal] ?? 0;
  if (signal === "neutral" || p < 0.45) return null;
  if (lens === "kind") {
    return { cls: `hl ${KIND_TONE[signal] ?? ""}`, alpha: p, tip: `reads as ${signal} · ${two(p)}` };
  }
  const target = a.evidence.comp?.[0]?.target;
  const agrees = signal === target;
  return {
    cls: `hl ${agrees ? "t-comp" : "t-comp-other"}`,
    alpha: p,
    tip: `points to ${signal} · ${two(p)}`,
  };
}

export function drawSheet(
  host: HTMLElement,
  m: Measurement,
  a: Assessment,
  lens: Lens,
  inspector: HTMLElement,
  hooks: SheetHooks,
): void {
  const body = m.body;
  const parts: (Node | string)[] = [];
  let cursor = 0;
  for (const unit of m.units) {
    if (unit.start < cursor) continue;
    parts.push(body.slice(cursor, unit.start));
    const text = body.slice(unit.start, unit.end);
    const look = unit.asked ? paint(m, a, unit, lens) : null;
    const cls = [
      "unit",
      unit.kind === "code" ? "u-code" : "",
      unit.kind === "heading" ? "u-heading" : "",
      look?.cls ?? "",
    ].join(" ");
    const el = h(
      "span",
      {
        class: cls,
        style: look ? `--a:${(0.18 + look.alpha * 0.55).toFixed(2)}` : null,
        title: look?.tip ?? null,
        tabindex: unit.asked ? 0 : null,
        "data-unit": unit.index,
      },
      text,
    );
    if (unit.asked) {
      const open = () => inspect(inspector, m, unit, hooks, host, el);
      el.addEventListener("click", open);
      el.addEventListener("keydown", (e) => {
        if ((e as KeyboardEvent).key === "Enter") open();
      });
    }
    parts.push(el);
    cursor = unit.end;
  }
  parts.push(body.slice(cursor));
  fill(host, body.trim() ? parts : h("em", { class: "faint" }, "The issue has no body."));
}

function inspect(
  panel: HTMLElement,
  m: Measurement,
  unit: Unit,
  hooks: SheetHooks,
  sheet: HTMLElement,
  el: HTMLElement,
): void {
  sheet.querySelectorAll(".unit.focused").forEach((u) => u.classList.remove("focused"));
  el.classList.add("focused");
  const kind = unitAnswer(m, unit, "kind");
  const comp = unitAnswer(m, unit, "comp");
  fill(
    panel,
    h("div", { class: "inspector-head" },
      h("span", { class: "eyebrow" }, `unit ${unit.index} · ${unit.kind}`),
      h("button", { class: "ghost small", type: "button", onclick: () => { panel.hidden = true; el.classList.remove("focused"); } }, "close"),
    ),
    h("blockquote", null, unit.text.length > 280 ? `${unit.text.slice(0, 280)}…` : unit.text),
    kind ? h("div", null, h("h4", null, "what kind of report this part signals"), distribution(kind.probabilities, kind.choice, { limit: 4 })) : null,
    comp ? h("div", null, h("h4", null, "which part of the project it points to"), distribution(comp.probabilities, comp.choice, { limit: 4 })) : null,
    h("p", { class: "faint small" },
      "Each unit is asked on its own, with the whole issue still in the state. ",
      "Removing it re-asks the decisions without it — a measured answer to ‘did this matter?’."),
    h("button", { class: "primary small", type: "button", onclick: () => hooks.onRemove([unit.index]) }, "Remove this and re-ask"),
  );
  panel.hidden = false;
}
