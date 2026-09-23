// The wait, staged: twelve docket lights filling while the bench mutters.

import { keyClick } from "./audio.js";
import { byId } from "./dom.js";

const MUTTERINGS = [
  "the bench is reading",
  "cross-referencing your priors",
  "twelve charges, one request",
  "a juror is unconvinced",
  "someone has fetched the big book",
  "checking whether a dog was involved",
  "weighing drama against substance",
  "the stamp is being inked",
];

/** One light per question on the docket. */
const CHARGES_HEARD = 12;
const TICK_MS = 260;

let theatre: ReturnType<typeof setInterval> | undefined;

export function beginDeliberation(): void {
  byId("deliberation").hidden = false;
  byId("verdict").hidden = true;
  byId("collapse").hidden = true;

  const lights = byId("lights");
  lights.innerHTML = "";
  const bulbs = Array.from({ length: CHARGES_HEARD }, () =>
    lights.appendChild(document.createElement("li")),
  );

  let lit = 0;
  let line = 0;
  theatre = setInterval(() => {
    if (lit < bulbs.length) {
      bulbs[lit++].classList.add("lit");
      keyClick();
    } else {
      bulbs.forEach((b) => b.classList.remove("lit"));
      lit = 0;
      byId("ticker").textContent = MUTTERINGS[++line % MUTTERINGS.length];
    }
  }, TICK_MS);
}

export function endDeliberation(): void {
  clearInterval(theatre);
  byId("deliberation").hidden = true;
}
