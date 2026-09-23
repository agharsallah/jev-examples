/* The "read it as" row: one button per reader. Picking one re-scores in code. */

import type { Audience } from "../api.js";
import { result as els } from "../elements.js";

function pill(audience: Audience, active: boolean, onPick: (key: string) => void): HTMLElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "pill";
  button.textContent = audience.label;
  button.setAttribute("aria-pressed", String(active));
  button.addEventListener("click", () => onPick(audience.key));
  return button;
}

export function drawPills(
  audiences: Audience[],
  activeKey: string,
  onPick: (key: string) => void,
): void {
  els.pills.replaceChildren(
    ...audiences.map((audience) => pill(audience, audience.key === activeKey, onPick)),
  );
}
