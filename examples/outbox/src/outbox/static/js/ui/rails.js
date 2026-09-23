/* "How it lands": one track per dimension, the reader's band behind the dot. */
import { escapeHtml } from "../dom.js";
import { result as els } from "../elements.js";
import { onScale, pct } from "../format.js";
function railClass(rail) {
    return "rail" + (rail.counted ? (rail.miss > 0 ? " off" : "") : " unsure");
}
/** The line under a track. Only a miss gets the reader's name in it. */
function noteHtml(rail, audienceLabel) {
    if (!rail.counted) {
        return `<b>unscored</b> — Jev is only ${pct(rail.confidence)} confident here, ` +
            `so it stays out of the total`;
    }
    if (rail.miss > 0) {
        return `${escapeHtml(rail.level)} — <b>${rail.verdict} for ${escapeHtml(audienceLabel)}</b>`;
    }
    return escapeHtml(rail.level);
}
function railRow(rail, audienceLabel) {
    const row = document.createElement("div");
    row.className = railClass(rail);
    row.innerHTML = `
      <span class="rail-name">${escapeHtml(rail.label)}</span>
      <div class="track">
        <div class="band-zone" style="left:${onScale(rail.low)};
             width:${onScale(rail.high - rail.low)}"></div>
        <div class="marker" style="left:${onScale(rail.score)}"></div>
      </div>
      <span class="rail-score">${rail.score.toFixed(2)}</span>`;
    const note = document.createElement("span");
    note.className = "rail-note";
    note.innerHTML = noteHtml(rail, audienceLabel);
    row.append(note);
    return row;
}
export function drawRails(rails, audienceLabel) {
    els.rails.replaceChildren(...rails.map((rail) => railRow(rail, audienceLabel)));
}
