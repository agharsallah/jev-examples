/* The few DOM helpers everything else leans on. */
/** An element that index.html promises exists; a missing one is a bug, loudly. */
export function byId(id) {
    const el = document.querySelector(`#${id}`);
    if (!el)
        throw new Error(`#${id} is missing from index.html`);
    return el;
}
export function show(el, visible) {
    el.hidden = !visible;
}
const ENTITIES = {
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
};
export function escapeHtml(text) {
    return text.replace(/[&<>"']/g, (c) => ENTITIES[c] ?? c);
}
/** Re-trigger a CSS animation on an element that already has the class. */
export function restartAnimation(el, className) {
    el.classList.remove(className);
    void el.offsetWidth; // force a reflow, or the browser merges the two changes
    el.classList.add(className);
}
