/* The handful of DOM helpers every part of the page shares. */
export function $(id) {
    const el = document.getElementById(id);
    if (!el)
        throw new Error(`no #${id} on the page`);
    return el;
}
/** Milliseconds as a scoreboard reads them. */
export const clock = (ms) => {
    const total = Math.floor(ms / 1000);
    return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
};
export function setTag(el, text, klass = "") {
    el.textContent = text;
    el.className = `tag ${klass}`.trim();
}
/** Set a number and replay its pop animation. */
export function bump(el, value) {
    el.textContent = String(value);
    el.classList.remove("pop");
    void el.offsetWidth;
    el.classList.add("pop");
}
