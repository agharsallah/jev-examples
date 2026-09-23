/* "Sentence by sentence": the draft on paper, each flagged sentence painted
 * over the exact characters Jev was asked about, and a legend for what showed. */
import { escapeHtml, show } from "../dom.js";
import { result as els } from "../elements.js";
import { pct, probeLabel } from "../format.js";
/** The hover text on a highlight: every probe asked about that sentence. */
function detail(sentence) {
    return Object.entries(sentence.probes)
        .map(([name, value]) => `${probeLabel(name)}: ${pct(value)}`)
        .join(" · ");
}
/** Walk the draft once, wrapping each flagged sentence where Jev found it. */
export function markDraft(draft, sentences) {
    let html = "";
    let cursor = 0;
    const used = new Set();
    for (const sentence of sentences) {
        if (!sentence.probe || sentence.start < cursor)
            continue;
        used.add(sentence.probe);
        html += escapeHtml(draft.slice(cursor, sentence.start));
        html += `<mark class="m-${sentence.probe}" title="${escapeHtml(detail(sentence))}">` +
            `${escapeHtml(draft.slice(sentence.start, sentence.end))}</mark>`;
        cursor = sentence.end;
    }
    html += escapeHtml(draft.slice(cursor));
    return { html, used };
}
function legendEntry(probe) {
    const entry = document.createElement("span");
    entry.innerHTML = `<i class="m-${probe}"></i> ${escapeHtml(probeLabel(probe))}`;
    return entry;
}
export function drawMarkup(draft, sentences) {
    show(els.markupBlock, sentences.length > 0);
    if (!sentences.length)
        return;
    els.sentenceNote.textContent =
        `${sentences.length} sentences, all asked about in one request`;
    const { html, used } = markDraft(draft, sentences);
    els.marked.innerHTML = html;
    els.legend.replaceChildren(...[...used].map(legendEntry));
}
