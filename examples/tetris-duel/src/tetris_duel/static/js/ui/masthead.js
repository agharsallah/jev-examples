/* The words around the wells: title, tagline, the level blurb, and the footer. */
import { $ } from "./dom.js";
const FAIR = " Both wells get the same seeded pieces and the same gravity, and points come from cleared rows only.";
export function title(left, right, yours) {
    document.querySelector("h1").innerHTML = `${left} <em>vs</em> ${right}`;
    document.title = `${left} vs ${right} — tetris duel`;
    document.querySelector(".masthead p").textContent = yours
        ? "One well plays itself. The other one is your problem."
        : "Two models, the same pieces, the same gravity. Sit back.";
    document.querySelectorAll(".keys, .pad").forEach((el) => (el.style.display = yours ? "" : "none"));
}
/** What each model at the table is told at this level, and how each of them is asked. */
export function describe(models, level) {
    $("blurb").innerHTML = models
        .map((p) => {
        const tier = p.levels.find((l) => l.key === level) ?? p.levels[p.levels.length - 1];
        return models.length > 1 ? `<b>${p.name}:</b> ${tier.blurb}` : tier.blurb;
    })
        .join("<br>");
    $("about").innerHTML = models.map((p) => p.about).join(" ") + FAIR;
}
