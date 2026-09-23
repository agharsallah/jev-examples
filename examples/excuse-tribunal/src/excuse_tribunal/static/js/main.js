// Front-of-house. The server does the judging; these modules do the theatre.
// This file only finds the controls and wires them to the modules that act.
import { bindSoundSwitch } from "./audio.js";
import { byId } from "./dom.js";
import { holdHearing } from "./hearing.js";
import { dealPlea } from "./pleas.js";
import { expunge, loadRecord } from "./record.js";
const form = byId("plea");
const submit = byId("submit");
const fields = {
    excuse: byId("excuse"),
    context: byId("context"),
    audience: byId("audience"),
};
bindSoundSwitch(byId("sound"));
form.addEventListener("submit", (event) => {
    event.preventDefault();
    void holdHearing(fields, submit);
});
byId("roll").addEventListener("click", () => dealPlea(fields));
byId("expunge").addEventListener("click", () => void expunge());
document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter")
        form.requestSubmit();
});
void loadRecord();
