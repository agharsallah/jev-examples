/* The whole result card, drawn from one payload. Each area has its own module;
 * this one decides the order and handles the two bits that belong to none. */

import type { Audience, MarkedSentence, Payload } from "../api.js";
import { restartAnimation, show } from "../dom.js";
import { result as els } from "../elements.js";
import { costLine } from "../format.js";
import { drawFindings } from "./findings.js";
import { drawMarkup } from "./markup.js";
import { drawPills } from "./pills.js";
import { drawRails } from "./rails.js";
import { drawVerdict } from "./verdict.js";

export interface ResultView {
  data: Payload;
  /** The sentence pass does not move on a rescore, so it is passed separately. */
  sentences: MarkedSentence[];
  rescored: boolean;
  audiences: Audience[];
  onPickReader: (key: string) => void;
}

/** The green note beside the reader buttons: which kind of work just happened. */
function drawRescoreNote(rescored: boolean): void {
  els.rescoreNote.textContent = rescored
    ? "same numbers, different reader — no model call"
    : "";
  if (rescored) restartAnimation(els.rescoreNote, "flash");
}

export function drawResult(view: ResultView): void {
  const { data, rescored } = view;
  drawVerdict(data);
  drawPills(view.audiences, data.audience.key, view.onPickReader);
  drawRails(data.rails, data.audience.label);
  drawFindings(data.findings);
  drawMarkup(data.draft, view.sentences);
  els.cost.textContent = costLine(data.cost, rescored);
  show(els.section, true);
  drawRescoreNote(rescored);
}
