// The few DOM helpers everything else leans on.
/** An element the page is known to contain; a missing one is a bug, not a state. */
export function byId(id) {
    const element = document.getElementById(id);
    if (!element)
        throw new Error(`#${id} is missing from the page`);
    return element;
}
const ENTITIES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };
/** Everything the accused typed ends up in innerHTML, so all of it goes through here. */
export function esc(text) {
    return text.replace(/[&<>"]/g, (c) => ENTITIES[c] ?? c);
}
/** Restart a CSS animation that is already applied, by forcing a reflow in between. */
export function replayAnimation(element, className) {
    element.classList.remove(className);
    void element.offsetWidth;
    element.classList.add(className);
}
