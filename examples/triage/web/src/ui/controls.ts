/* The policy's knobs. Moving one sends the same measurement back to be
 * rescored: the verdict changes, the answers do not, and Jev is not asked. */

import type { Settings } from "../api.js";
import { h } from "../dom.js";
import { two } from "../format.js";

const KNOBS: [key: string, label: string, help: string][] = [
  ["choice_apply", "apply a family label at", "Choice confidence needed to apply without asking"],
  ["choice_floor", "leave unlabelled below", "below this a family gets no label, and an unsure kind goes to a human"],
  ["noul_apply", "apply an attribute label at", "Noul probability for labels like ‘good first issue’"],
  ["present", "checklist item counts at", "Noul probability that a repro, version… is present"],
  ["dup_same", "call it a duplicate at", "‘same problem’ probability"],
  ["security", "treat as security at", "‘security-sensitive’ probability"],
];

const WEIGHTS: [key: string, label: string][] = [
  ["impact", "impact"],
  ["actionability", "actionability"],
  ["frustration", "frustration"],
];

export function controls(settings: Settings, defaults: Settings, onChange: (s: Settings, reset?: boolean) => void) {
  const current: Settings = structuredClone(settings);
  let timer: number | undefined;
  const changed = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => onChange(structuredClone(current)), 120);
  };

  const slider = (value: number, set: (v: number) => void, label: string, help: string) => {
    const out = h("output", null, two(value));
    const input = h("input", { type: "range", min: 0, max: 1, step: 0.01, value, "aria-label": label });
    input.addEventListener("input", () => {
      const v = Number(input.value);
      out.textContent = two(v);
      set(v);
      changed();
    });
    return h("label", { class: "knob", title: help }, h("span", null, label), input, out);
  };

  return h(
    "section",
    { class: "card" },
    h("header", { class: "card-head" }, h("h3", null, "Policy knobs"), h("span", { class: "card-note" }, "rescored locally · no new request")),
    ...KNOBS.map(([key, label, help]) =>
      slider(current[key] as number, (v) => (current[key] = v), label, help),
    ),
    h("div", { class: "eyebrow" }, "priority weights"),
    ...WEIGHTS.map(([key, label]) =>
      slider(current.weights[key] ?? 0, (v) => (current.weights[key] = v), label, `weight on the ${label} score`),
    ),
    h("button", {
      class: "ghost small",
      type: "button",
      onclick: () => onChange(structuredClone(defaults), true),
    }, "reset to defaults"),
  );
}
