/* Every element the script touches, looked up once and typed. index.html is
 * the other half of this file: an id renamed there has to be renamed here. */

import { byId } from "./dom.js";

export const composer = {
  form: byId<HTMLFormElement>("composer"),
  draft: byId<HTMLTextAreaElement>("draft"),
  to: byId<HTMLInputElement>("to"),
  goal: byId<HTMLInputElement>("goal"),
  channel: byId<HTMLSelectElement>("channel"),
  deep: byId<HTMLInputElement>("deep"),
  send: byId<HTMLButtonElement>("send"),
  sample: byId<HTMLButtonElement>("sample"),
  charcount: byId("charcount"),
};

export const status = {
  thinking: byId("thinking"),
  thinkingText: byId("thinkingText"),
  error: byId("error"),
};

export const result = {
  section: byId("result"),
  stamp: byId("stamp"),
  verdictWord: byId("verdictWord"),
  verdictBlurb: byId("verdictBlurb"),
  dial: byId("dial"),
  dialValue: byId<SVGCircleElement>("dialValue"),
  scoreValue: byId("scoreValue"),
  intentChip: byId("intentChip"),
  riskChip: byId("riskChip"),
  pills: byId("audiencePills"),
  wants: byId("wants"),
  rescoreNote: byId("rescoreNote"),
  fitValue: byId("fitValue"),
  rails: byId("rails"),
  findings: byId("findings"),
  findingsBlock: byId("findingsBlock"),
  marked: byId("marked"),
  legend: byId("legend"),
  markupBlock: byId("markupBlock"),
  sentenceNote: byId("sentenceNote"),
  cost: byId("cost"),
};
