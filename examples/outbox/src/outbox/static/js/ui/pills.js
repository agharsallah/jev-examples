/* The "read it as" row: one button per reader. Picking one re-scores in code. */
import { result as els } from "../elements.js";
function pill(audience, active, onPick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "pill";
    button.textContent = audience.label;
    button.setAttribute("aria-pressed", String(active));
    button.addEventListener("click", () => onPick(audience.key));
    return button;
}
export function drawPills(audiences, activeKey, onPick) {
    els.pills.replaceChildren(...audiences.map((audience) => pill(audience, audience.key === activeKey, onPick)));
}
