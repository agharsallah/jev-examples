// One hearing, start to finish: read the form, stage the wait, show the outcome.

import { judge, type Plea } from "./api.js";
import { beginDeliberation, endDeliberation } from "./deliberation.js";
import type { PleaFields } from "./pleas.js";
import { loadRecord } from "./record.js";
import { collapse, showVerdict } from "./verdict.js";

/** Blank optional fields are sent as null, which the server reads as "not given". */
export function readPlea(fields: PleaFields): Plea {
  return {
    excuse: fields.excuse.value.trim(),
    context: fields.context.value.trim() || null,
    audience: fields.audience.value.trim() || null,
  };
}

export async function holdHearing(fields: PleaFields, submit: HTMLButtonElement): Promise<void> {
  const plea = readPlea(fields);
  if (!plea.excuse) return;

  submit.disabled = true;
  beginDeliberation();
  try {
    const outcome = await judge(plea);
    endDeliberation();
    if (!outcome.ok) collapse(outcome.message);
    else {
      showVerdict(outcome.verdict);
      void loadRecord();
    }
  } catch (error) {
    endDeliberation();
    collapse(`The courtroom is unreachable: ${(error as Error).message}`);
  } finally {
    submit.disabled = false;
  }
}
