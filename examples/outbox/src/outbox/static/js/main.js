/* The desk, client side.
 *
 * Two kinds of work happen here. Reading a draft goes to /api/read, which calls
 * Jev. Changing who the draft is for goes to /api/rescore, which does not --
 * the same measurements, weighed against a different reader. The little green
 * note next to the reader buttons says which one just happened.
 *
 * This file only holds the state and wires events to the modules that draw. */
import { fetchDesk, readDraft, rescoreDraft } from "./api.js";
import { composer } from "./elements.js";
import * as form from "./ui/composer.js";
import { drawResult } from "./ui/result.js";
let config = { audiences: [], samples: [] };
let current = null; // the last payload from /api/read or /api/rescore
let sentences = []; // kept across a rescore: the sentence pass does not move
let sampleIndex = 0;
function present(data, rescored = false) {
    current = data;
    if (data.sentences.length)
        sentences = data.sentences;
    drawResult({ data, sentences, rescored, audiences: config.audiences, onPickReader: rescore });
}
function errorText(error) {
    return error instanceof Error ? error.message : String(error);
}
async function read(event) {
    event?.preventDefault();
    const body = form.readForm();
    if (!body)
        return;
    form.startBusy(body.deep);
    sentences = [];
    try {
        present(await readDraft(body));
    }
    catch (error) {
        form.showError(errorText(error));
    }
    finally {
        form.stopBusy();
    }
}
async function rescore(audienceKey) {
    if (!current || audienceKey === current.audience.key)
        return;
    try {
        present(await rescoreDraft(current.measurement, audienceKey), true);
    }
    catch (error) {
        form.showError(errorText(error));
    }
}
function nextSample() {
    if (!config.samples.length)
        return; // /api/desk has not answered yet
    form.fillSample(config.samples[sampleIndex % config.samples.length]);
    sampleIndex += 1;
}
composer.form.addEventListener("submit", read);
composer.sample.addEventListener("click", nextSample);
composer.draft.addEventListener("input", form.updateCharCount);
document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter")
        void read(event);
});
void fetchDesk().then((data) => { config = data; });
