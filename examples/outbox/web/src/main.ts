/* The desk, client side.
 *
 * Two kinds of work happen here. Reading a draft goes to /api/read, which calls
 * Jev. Changing who the draft is for goes to /api/rescore, which does not --
 * the same measurements, weighed against a different reader. The little green
 * note next to the reader buttons says which one just happened.
 *
 * This file only holds the state and wires events to the modules that draw. */

import { fetchDesk, readDraft, rescoreDraft } from "./api.js";
import type { DeskConfig, MarkedSentence, Payload } from "./api.js";
import { composer } from "./elements.js";
import * as form from "./ui/composer.js";
import { drawResult } from "./ui/result.js";

let config: DeskConfig = { audiences: [], samples: [] };
let current: Payload | null = null; // the last payload from /api/read or /api/rescore
let sentences: MarkedSentence[] = []; // kept across a rescore: the sentence pass does not move
let sampleIndex = 0;

function present(data: Payload, rescored = false): void {
  current = data;
  if (data.sentences.length) sentences = data.sentences;
  drawResult({ data, sentences, rescored, audiences: config.audiences, onPickReader: rescore });
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

async function read(event?: Event): Promise<void> {
  event?.preventDefault();
  const body = form.readForm();
  if (!body) return;

  form.startBusy(body.deep);
  sentences = [];
  try {
    present(await readDraft(body));
  } catch (error) {
    form.showError(errorText(error));
  } finally {
    form.stopBusy();
  }
}

async function rescore(audienceKey: string): Promise<void> {
  if (!current || audienceKey === current.audience.key) return;
  try {
    present(await rescoreDraft(current.measurement, audienceKey), true);
  } catch (error) {
    form.showError(errorText(error));
  }
}

function nextSample(): void {
  if (!config.samples.length) return; // /api/desk has not answered yet
  form.fillSample(config.samples[sampleIndex % config.samples.length]);
  sampleIndex += 1;
}

composer.form.addEventListener("submit", read);
composer.sample.addEventListener("click", nextSample);
composer.draft.addEventListener("input", form.updateCharCount);

document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") void read(event);
});

void fetchDesk().then((data) => { config = data; });
