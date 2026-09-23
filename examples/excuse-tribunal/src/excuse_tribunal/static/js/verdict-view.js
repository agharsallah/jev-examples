// The ruling sheet as markup. Pure: a verdict in, an HTML string out, so the
// layout can be read top to bottom without any DOM in the way.
import { esc } from "./dom.js";
import { barWidth, pct } from "./format.js";
/** Charges are read out one after another, after the stamp has landed. */
const FIRST_CHARGE_DELAY_S = 0.35;
const CHARGE_STAGGER_S = 0.09;
/** A labelled bar on the 0-4 scale; the width is applied later so it can animate in. */
export function meter(name, value, detail, blue = false) {
    return `<div class="meter">
    <div class="meter-name">${esc(name)}</div>
    <div class="meter-bar">
      <div class="track${blue ? " blue" : ""}"><div class="fill" data-width="${barWidth(value)}"></div></div>
      <div class="meter-detail">${esc(detail)}</div>
    </div>
  </div>`;
}
function charge(c, i) {
    return `<li class="${c.against ? "against" : "for"}" style="animation-delay:${FIRST_CHARGE_DELAY_S + i * CHARGE_STAGGER_S}s">
         <span class="mark">${c.against ? "✗" : "✓"}</span>
         <span>${esc(c.label)}</span><span class="leader"></span>
         <span class="pct">${pct(c.probability)}</span></li>`;
}
function charges(list) {
    return list.length
        ? list.map(charge).join("")
        : `<li><span class="mark">·</span><span>Nothing on the record either way.</span></li>`;
}
function remarks(list) {
    if (!list.length)
        return "";
    return `<p class="block-name">the bench notes</p>
      <ul class="remarks">${list.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>`;
}
export function verdictSheet(v) {
    return `
    <div class="sheet-head">
      <span class="form-no">form e&#8209;2</span>
      <span class="sheet-title">ruling of the bench</span>
      <span class="copy-mark">entered in the record</span>
    </div>
    <div class="ruling slam" data-ruling="${esc(v.ruling)}">${esc(v.ruling)}</div>
    <p class="headline">${esc(v.headline)}</p>
    <p class="quoted">“${esc(v.excuse)}”</p>

    <p class="block-name">the measurements</p>
    ${v.measures.map((m) => meter(m.label, m.value, m.detail)).join("")}

    <p class="block-name">reading of the charges</p>
    <ul class="charges">${charges(v.charges)}</ul>

    <p class="block-name">filed as</p>
    <p class="filed"><strong>${esc(v.archetype.name)}</strong> — confidence ${pct(v.archetype.confidence)}</p>
    ${v.archetype.ranked.map((a) => meter(a.name, a.probability * 4, pct(a.probability), true)).join("")}

    <div class="sentence"><span>sentence</span><p>${esc(v.sentence)}</p></div>
    ${remarks(v.remarks)}
    <p class="confidence">Jev's confidence in the believability reading: ${pct(v.confidence)}.
      ${v.mistrial ? "Below the floor the court will act on, so no sentence was passed." : ""}</p>`;
}
