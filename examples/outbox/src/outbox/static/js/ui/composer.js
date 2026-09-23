/* The left-hand form: reading what was typed, filling in a sample, and the
 * busy / error states that sit beside the result card. */
import { show } from "../dom.js";
import { composer as els, result, status } from "../elements.js";
/** What /api/read is sent, or null when there is no draft to read. */
export function readForm() {
    const draft = els.draft.value.trim();
    if (!draft)
        return null;
    return {
        draft,
        to: els.to.value.trim() || null,
        goal: els.goal.value.trim() || null,
        channel: els.channel.value || null,
        deep: els.deep.checked,
    };
}
export function fillSample(sample) {
    els.draft.value = sample.draft;
    els.to.value = sample.to || "";
    els.goal.value = sample.goal || "";
    // A sample's channel may not be one the dropdown offers; fall back to blank.
    els.channel.value = [...els.channel.options].some((o) => o.value === sample.channel)
        ? sample.channel ?? ""
        : "";
    els.draft.dispatchEvent(new Event("input"));
    els.draft.focus();
}
export function updateCharCount() {
    els.charcount.textContent = `${els.draft.value.length} characters`;
}
/** Hide the old result and say what is being asked while the request runs. */
export function startBusy(deep) {
    show(status.error, false);
    show(result.section, false);
    show(status.thinking, true);
    status.thinkingText.textContent = deep
        ? "reading the draft, then every sentence in it…"
        : "reading the draft…";
    els.send.disabled = true;
}
export function stopBusy() {
    show(status.thinking, false);
    els.send.disabled = false;
}
export function showError(message) {
    status.error.textContent = message;
    show(status.error, true);
}
