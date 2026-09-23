/* The "what X said about this piece" card: one per model at the table.
 *
 * The page ships one card. A second model gets a copy of it, with every id
 * prefixed, so both cards are the same markup and this class drives either.
 */

import type { Option, Plan } from "../api.js";
import { $ } from "./dom.js";

const COPY_ID = "rivalThinking";
const COPY_PREFIX = "rival_";

export class ThinkingCard {
  private constructor(
    readonly root: HTMLElement,
    private readonly prefix: string
  ) {}

  /** The card that is in the page. */
  static original(): ThinkingCard {
    return new ThinkingCard($("thinking"), "");
  }

  /** A second card under the first, made once and reused. */
  static copy(): ThinkingCard {
    let root = document.getElementById(COPY_ID);
    if (!root) {
      const original = $("thinking");
      root = original.cloneNode(true) as HTMLElement;
      root.id = COPY_ID;
      root.querySelectorAll<HTMLElement>("[id]").forEach((el) => (el.id = `${COPY_PREFIX}${el.id}`));
      original.after(root);
    }
    return new ThinkingCard(root, COPY_PREFIX);
  }

  static removeCopy(): void {
    document.getElementById(COPY_ID)?.remove();
  }

  private q(id: string): HTMLElement {
    return $(`${this.prefix}${id}`);
  }

  /** Back to the empty state, for a new player at this well. */
  reset(name: string, side: string): void {
    this.root.querySelectorAll("[data-player]").forEach((el) => (el.textContent = name));
    this.q("chatter").textContent = `Press start and ${name} takes the ${side}-hand well.`;
    this.q("bars").innerHTML = `<p class="empty">The landings ${name} weighed up will show up here.</p>`;
    this.q("pick").textContent = "";
    this.q("overrule").hidden = true;
    this.q("error").hidden = true;
    this.q("modelNote").textContent = "one request per piece";
    for (const name of ["danger", "clear", "slot", "conf"]) this.meter(name, 0, "—");
    this.q("slotMeter").hidden = true;
  }

  error(message: string): void {
    const box = this.q("error");
    box.hidden = false;
    box.textContent = message;
  }

  hideError(): void {
    this.q("error").hidden = true;
  }

  /** Everything behind one move: the pick, the runners-up, and the readings. */
  show(plan: Plan, ms: number, who: string): void {
    this.hideError();
    this.q("chatter").textContent = plan.mood.line;
    this.q("pick").innerHTML = pickLine(plan, who);

    const overrule = this.q("overrule");
    overrule.hidden = !plan.overruled;
    if (plan.overruled) overrule.textContent = plan.note;

    const bars = this.q("bars");
    bars.innerHTML = "";
    for (const option of plan.options) bars.appendChild(bar(option));

    this.meter("danger", plan.danger.value / 4, `${plan.danger.value.toFixed(2)} / 4`);
    this.q("dangerNote").textContent = plan.danger.level;
    this.meter("clear", plan.clear_now, percent(plan.clear_now));
    const slot = this.q("slotMeter");
    slot.hidden = plan.keep_slot === null || plan.keep_slot === undefined;
    if (!slot.hidden) {
      this.meter("slot", plan.keep_slot!, percent(plan.keep_slot!));
      this.q("slotNote").textContent = plan.guarding
        ? `column ${plan.guarding} is being kept clear for a four-row clear`
        : "not worth waiting for a bar right now";
    }
    this.meter("conf", plan.confidence, percent(plan.confidence));

    const tokens = plan.usage.input_tokens ?? 0;
    this.q("modelNote").textContent = `${plan.model} · ${tokens} input tokens · ${ms}ms`;
  }

  private meter(name: string, fraction: number, text: string): void {
    this.q(`${name}Fill`).style.width = `${Math.min(100, Math.max(0, fraction * 100))}%`;
    this.q(`${name}Value`).textContent = text;
  }
}

const percent = (fraction: number): string => `${Math.round(fraction * 100)}%`;

function pickLine(plan: Plan, who: string): string {
  return (
    `<b>${plan.piece}</b> → ${plan.where} · chosen from <b>${plan.menu_size}</b> legal landings` +
    (plan.rows_cleared ? ` · clears <b>${plan.rows_cleared}</b>` : "") +
    (plan.torn ? ` · <b>${who} is torn</b>` : "") +
    (plan.sure ? " · sure enough to <b>hard drop</b> it" : "") +
    (plan.guarding ? ` · holding <b>column ${plan.guarding}</b> open` : "")
  );
}

function bar(option: Option): HTMLElement {
  const el = document.createElement("div");
  el.className = `bar${option.jev ? " is-pick" : ""}${option.chosen ? " is-taken" : ""}`;
  el.innerHTML =
    `<span class="pct">${percent(option.probability)}</span>` +
    `<span class="track"><span class="fill" style="width:${Math.max(3, option.probability * 100)}%"></span>` +
    `<span class="label">${option.where}${option.rows_cleared ? ` · clears ${option.rows_cleared}` : ""}` +
    `${option.new_gaps ? ` · buries ${option.new_gaps}` : ""}</span></span>`;
  return el;
}
