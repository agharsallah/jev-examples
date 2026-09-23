/* The top of the result card: the stamp, the dial, the two chips. */
import { escapeHtml } from "../dom.js";
import { result as els } from "../elements.js";
import { humanise, pct, verdictClass } from "../format.js";
// The dial's circle has r=52 in index.html; its dasharray in the CSS matches.
const DIAL_CIRCUMFERENCE = 2 * Math.PI * 52;
export function drawVerdict(data) {
    els.verdictWord.textContent = data.verdict;
    els.verdictBlurb.textContent = data.blurb;
    const klass = verdictClass(data.verdict);
    els.stamp.className = `stamp ${klass}`;
    els.dial.className = `dial ${klass}`;
    els.scoreValue.textContent = String(data.sendScore);
    els.dialValue.style.strokeDashoffset =
        String(DIAL_CIRCUMFERENCE * (1 - data.sendScore / 100));
    els.intentChip.innerHTML =
        `reads as <b>${escapeHtml(humanise(data.intent.choice))}</b> ` +
            `<span>${pct(data.intent.confidence)} confident</span>`;
    els.riskChip.innerHTML =
        `most likely failure: <b>${escapeHtml(humanise(data.risk.choice))}</b> ` +
            `<span>${pct(data.risk.confidence)}</span>`;
    els.fitValue.textContent = `${data.fit}/100`;
    els.wants.textContent = `${data.audience.label} wants ${data.audience.wants}`;
}
