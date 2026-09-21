// Front-of-house. The server does the judging; this file does the theatre.

const $ = (id) => document.getElementById(id);
const form = $("plea");
const verdictEl = $("verdict");
const deliberation = $("deliberation");
const collapseEl = $("collapse");

const PLEAS = [
  ["my calendar was in the wrong timezone and so, briefly, was I", "join the standup", "my team"],
  ["the dog ate my migration", "ship the database change", "my manager"],
  ["mercury is retrograde and my branch reflects that", "finish the release", "the client"],
  ["I did write it. Then I force-pushed over it. Then I wrote it again, worse.", "deliver the report", "my tech lead"],
  ["the train was cancelled, then my laptop died, then honestly I forgot", "be at the review", "my manager"],
  ["I was on a call with someone who was also on a call", "reply to the email", "a client"],
  ["nothing happened. I simply did not do it.", "do it", "my manager"],
  ["docker desktop asked me to update and I have not been seen since", "run the tests", "my team"],
];

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

/* ---- courtroom audio: no files, just oscillators ---- */

let audio = null;
const wanted = () => $("sound").checked;

function ctx() {
  if (!audio) audio = new (window.AudioContext || window.webkitAudioContext)();
  return audio;
}

function tone(freq, duration, type = "sine", gain = 0.08, slideTo = null) {
  if (!wanted()) return;
  const ac = ctx();
  const osc = ac.createOscillator();
  const vol = ac.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, ac.currentTime);
  if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, ac.currentTime + duration);
  vol.gain.setValueAtTime(gain, ac.currentTime);
  vol.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + duration);
  osc.connect(vol).connect(ac.destination);
  osc.start();
  osc.stop(ac.currentTime + duration);
}

const keyClick = () => tone(1800 + Math.random() * 400, 0.03, "square", 0.02);
const thud = () => { tone(180, 0.22, "triangle", 0.22, 40); tone(90, 0.3, "sine", 0.18, 30); };
const ding = () => { tone(1320, 0.5, "sine", 0.06); tone(1980, 0.4, "sine", 0.03); };

/* ---- deliberation ---- */

let theatre = null;

function beginDeliberation() {
  deliberation.hidden = false;
  verdictEl.hidden = true;
  collapseEl.hidden = true;
  const lights = $("lights");
  lights.innerHTML = "";
  const bulbs = Array.from({ length: 12 }, () => lights.appendChild(document.createElement("li")));

  let lit = 0;
  let line = 0;
  theatre = setInterval(() => {
    if (lit < bulbs.length) {
      bulbs[lit++].classList.add("lit");
      keyClick();
    } else {
      bulbs.forEach((b) => b.classList.remove("lit"));
      lit = 0;
      $("ticker").textContent = MUTTERINGS[++line % MUTTERINGS.length];
    }
  }, 260);
}

function endDeliberation() {
  clearInterval(theatre);
  deliberation.hidden = true;
}

/* ---- rendering the sheet ---- */

const pct = (p) => `${Math.round(p * 100)}%`;
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function meter(name, value, detail, blue = false) {
  return `<div class="meter">
    <div class="meter-name">${esc(name)}</div>
    <div class="meter-bar">
      <div class="track${blue ? " blue" : ""}"><div class="fill" data-width="${Math.max(0, Math.min(1, value / 4)) * 100}"></div></div>
      <div class="meter-detail">${esc(detail)}</div>
    </div>
  </div>`;
}

function showVerdict(v) {
  const charges = v.charges.length
    ? v.charges.map((c, i) => `<li class="${c.against ? "against" : "for"}" style="animation-delay:${0.35 + i * 0.09}s">
         <span class="mark">${c.against ? "✗" : "✓"}</span>
         <span>${esc(c.label)}</span><span class="leader"></span>
         <span class="pct">${pct(c.probability)}</span></li>`).join("")
    : `<li><span class="mark">·</span><span>Nothing on the record either way.</span></li>`;

  verdictEl.innerHTML = `
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
    <ul class="charges">${charges}</ul>

    <p class="block-name">filed as</p>
    <p class="filed"><strong>${esc(v.archetype.name)}</strong> — confidence ${pct(v.archetype.confidence)}</p>
    ${v.archetype.ranked.map((a) => meter(a.name, a.probability * 4, pct(a.probability), true)).join("")}

    <div class="sentence"><span>sentence</span><p>${esc(v.sentence)}</p></div>
    ${v.remarks.length ? `<p class="block-name">the bench notes</p>
      <ul class="remarks">${v.remarks.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>` : ""}
    <p class="confidence">Jev's confidence in the believability reading: ${pct(v.confidence)}.
      ${v.mistrial ? "Below the floor the court will act on, so no sentence was passed." : ""}</p>`;

  verdictEl.hidden = false;
  thud();
  verdictEl.classList.remove("shaken");
  void verdictEl.offsetWidth;
  verdictEl.classList.add("shaken");
  // Let the bars start at zero so the fill reads as the court measuring.
  requestAnimationFrame(() => {
    verdictEl.querySelectorAll(".fill").forEach((f) => { f.style.width = `${f.dataset.width}%`; });
  });
  setTimeout(ding, 650);
  verdictEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function collapse(message) {
  collapseEl.textContent = `The hearing collapsed.\n${message}`;
  collapseEl.hidden = false;
}

/* ---- the record ---- */

async function loadRecord() {
  const data = await fetch("/api/record").then((r) => r.json());
  const panel = $("record");
  if (!data.hearings.length) { panel.hidden = true; return; }
  panel.hidden = false;
  const s = data.summary;
  $("record-stats").textContent =
    `${s.hearings} hearings · average believability ${s.average_believability.toFixed(2)} / 4 · signature move: ${s.signature_move}`;
  $("priors").innerHTML = data.hearings.map((h) => `<li>
      <span class="when">${esc(h.when.slice(0, 16).replace("T", " "))}</span>
      <span class="said">${esc(h.excuse)}</span>
      <span class="outcome" data-ruling="${esc(h.ruling)}">${esc(h.ruling.toLowerCase())} · ${esc(h.archetype)}</span>
    </li>`).join("");
}

/* ---- wiring ---- */

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const excuse = $("excuse").value.trim();
  if (!excuse) return;

  $("submit").disabled = true;
  beginDeliberation();
  try {
    const response = await fetch("/api/judge", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ excuse, context: $("context").value.trim() || null, audience: $("audience").value.trim() || null }),
    });
    const data = await response.json();
    endDeliberation();
    if (!response.ok) collapse(data.error || `The clerk returned ${response.status}.`);
    else { showVerdict(data); loadRecord(); }
  } catch (error) {
    endDeliberation();
    collapse(`The courtroom is unreachable: ${error.message}`);
  } finally {
    $("submit").disabled = false;
  }
});

$("roll").addEventListener("click", () => {
  const [excuse, context, audience] = PLEAS[Math.floor(Math.random() * PLEAS.length)];
  $("excuse").value = "";
  $("context").value = context;
  $("audience").value = audience;
  // Typed out, because a plea should be seen being made.
  let i = 0;
  const typing = setInterval(() => {
    $("excuse").value = excuse.slice(0, ++i);
    if (i % 2 === 0) keyClick();
    if (i >= excuse.length) clearInterval(typing);
  }, 18);
});

$("expunge").addEventListener("click", async () => {
  if (!confirm("Destroy the record? The court does not endorse this.")) return;
  await fetch("/api/record", { method: "DELETE" });
  loadRecord();
});

document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") form.requestSubmit();
});

loadRecord();
