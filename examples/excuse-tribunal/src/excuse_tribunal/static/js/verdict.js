// Putting the ruling down on the bench: the sheet, the thud, the bars filling.
import { ding, thud } from "./audio.js";
import { byId, replayAnimation } from "./dom.js";
import { verdictSheet } from "./verdict-view.js";
/** The ding waits for the stamp to settle. */
const DING_AFTER_MS = 650;
export function showVerdict(v) {
    const sheet = byId("verdict");
    sheet.innerHTML = verdictSheet(v);
    sheet.hidden = false;
    thud();
    replayAnimation(sheet, "shaken");
    // Let the bars start at zero so the fill reads as the court measuring.
    requestAnimationFrame(() => {
        sheet.querySelectorAll(".fill").forEach((f) => {
            f.style.width = `${f.dataset.width}%`;
        });
    });
    setTimeout(ding, DING_AFTER_MS);
    sheet.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
/** When there is no verdict to give, say so in the court's own red. */
export function collapse(message) {
    const notice = byId("collapse");
    notice.textContent = `The hearing collapsed.\n${message}`;
    notice.hidden = false;
}
