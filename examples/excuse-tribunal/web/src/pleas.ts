// "Deal me a plea": a canned excuse, typed out where the accused can see it.

import { keyClick } from "./audio.js";

/** [excuse, what was expected, who is being told]. */
type CannedPlea = readonly [excuse: string, context: string, audience: string];

const PLEAS: readonly CannedPlea[] = [
  ["my calendar was in the wrong timezone and so, briefly, was I", "join the standup", "my team"],
  ["the dog ate my migration", "ship the database change", "my manager"],
  ["mercury is retrograde and my branch reflects that", "finish the release", "the client"],
  ["I did write it. Then I force-pushed over it. Then I wrote it again, worse.", "deliver the report", "my tech lead"],
  ["the train was cancelled, then my laptop died, then honestly I forgot", "be at the review", "my manager"],
  ["I was on a call with someone who was also on a call", "reply to the email", "a client"],
  ["nothing happened. I simply did not do it.", "do it", "my manager"],
  ["docker desktop asked me to update and I have not been seen since", "run the tests", "my team"],
];

export interface PleaFields {
  excuse: HTMLTextAreaElement;
  context: HTMLInputElement;
  audience: HTMLInputElement;
}

const pick = (): CannedPlea => PLEAS[Math.floor(Math.random() * PLEAS.length)];

export function dealPlea(fields: PleaFields): void {
  const [excuse, context, audience] = pick();
  fields.excuse.value = "";
  fields.context.value = context;
  fields.audience.value = audience;
  // Typed out, because a plea should be seen being made.
  let i = 0;
  const typing = setInterval(() => {
    fields.excuse.value = excuse.slice(0, ++i);
    if (i % 2 === 0) keyClick();
    if (i >= excuse.length) clearInterval(typing);
  }, 18);
}
