// The prior-offences panel: the last twenty hearings, newest first.
import { expungeRecord, fetchRecord } from "./api.js";
import { byId, esc } from "./dom.js";
import { hearingTime, recordStats } from "./format.js";
function prior(h) {
    return `<li>
      <span class="when">${esc(hearingTime(h.when))}</span>
      <span class="said">${esc(h.excuse)}</span>
      <span class="outcome" data-ruling="${esc(h.ruling)}">${esc(h.ruling.toLowerCase())} · ${esc(h.archetype)}</span>
    </li>`;
}
export async function loadRecord() {
    const data = await fetchRecord();
    const panel = byId("record");
    if (!data.hearings.length) {
        panel.hidden = true;
        return;
    }
    panel.hidden = false;
    byId("record-stats").textContent = recordStats(data.summary);
    byId("priors").innerHTML = data.hearings.map(prior).join("");
}
export async function expunge() {
    if (!confirm("Destroy the record? The court does not endorse this."))
        return;
    await expungeRecord();
    await loadRecord();
}
