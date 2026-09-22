/* The desk, client side.
 *
 * Two kinds of work happen here. Reading a draft goes to /api/read, which calls
 * Jev. Changing who the draft is for goes to /api/rescore, which does not --
 * the same measurements, weighed against a different reader. The little green
 * note next to the reader buttons says which one just happened. */

const $ = (id) => document.getElementById(id);

const els = {
  form: $("composer"), draft: $("draft"), to: $("to"), goal: $("goal"),
  channel: $("channel"), deep: $("deep"), send: $("send"), sample: $("sample"),
  charcount: $("charcount"), result: $("result"), thinking: $("thinking"),
  thinkingText: $("thinkingText"), error: $("error"), stamp: $("stamp"),
  verdictWord: $("verdictWord"), verdictBlurb: $("verdictBlurb"), dial: $("dial"),
  dialValue: $("dialValue"), scoreValue: $("scoreValue"), intentChip: $("intentChip"),
  riskChip: $("riskChip"), pills: $("audiencePills"), wants: $("wants"),
  rescoreNote: $("rescoreNote"), fitValue: $("fitValue"), rails: $("rails"),
  findings: $("findings"), findingsBlock: $("findingsBlock"), marked: $("marked"),
  legend: $("legend"), markupBlock: $("markupBlock"), cost: $("cost"),
  sentenceNote: $("sentenceNote"),
};

const VERDICT_CLASS = {
  "SEND IT": "v-send",
  "TIGHTEN IT": "v-tighten",
  "REWRITE IT": "v-rewrite",
  "DO NOT SEND": "v-hold",
  UNREADABLE: "v-unclear",
};

const GLYPH = { blocker: "!!", major: "!", minor: "·", good: "✓" };

const PROBE_LABEL = {
  carries_the_ask: "the ask",
  barbed: "reads as pointed",
  hedged: "hedging",
  ambiguous: "ambiguous",
  sensitive: "should not be here",
  cuttable: "could go",
};

const DIAL_CIRCUMFERENCE = 2 * Math.PI * 52;

let config = { audiences: [], samples: [] };
let current = null;   // the last payload from /api/read or /api/rescore
let sentences = [];   // kept across a rescore: the sentence pass does not move
let sampleIndex = 0;

/* ----------------------------------------------------------- helpers */

const pct = (value) => `${Math.round(value * 100)}%`;
const onScale = (value) => `${(value / 4) * 100}%`;

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function show(el, visible) { el.hidden = !visible; }

/* ----------------------------------------------------------- drawing */

function drawVerdict(data) {
  els.verdictWord.textContent = data.verdict;
  els.verdictBlurb.textContent = data.blurb;
  const klass = VERDICT_CLASS[data.verdict] || "v-unclear";
  els.stamp.className = `stamp ${klass}`;
  els.dial.className = `dial ${klass}`;

  els.scoreValue.textContent = data.sendScore;
  els.dialValue.style.strokeDashoffset =
    DIAL_CIRCUMFERENCE * (1 - data.sendScore / 100);

  els.intentChip.innerHTML =
    `reads as <b>${escapeHtml(data.intent.choice.replace(/_/g, " "))}</b> ` +
    `<span>${pct(data.intent.confidence)} confident</span>`;
  els.riskChip.innerHTML =
    `most likely failure: <b>${escapeHtml(data.risk.choice.replace(/_/g, " "))}</b> ` +
    `<span>${pct(data.risk.confidence)}</span>`;

  els.fitValue.textContent = `${data.fit}/100`;
  els.wants.textContent = `${data.audience.label} wants ${data.audience.wants}`;
}

function drawRails(rails, audienceLabel) {
  els.rails.innerHTML = "";
  for (const rail of rails) {
    const row = document.createElement("div");
    row.className = "rail" + (rail.counted ? (rail.miss > 0 ? " off" : "") : " unsure");
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
    if (!rail.counted) {
      note.innerHTML =
        `<b>unscored</b> — Jev is only ${pct(rail.confidence)} confident here, ` +
        `so it stays out of the total`;
    } else if (rail.miss > 0) {
      note.innerHTML =
        `${escapeHtml(rail.level)} — <b>${rail.verdict} for ${escapeHtml(audienceLabel)}</b>`;
    } else {
      note.textContent = rail.level;
    }
    row.append(note);
    els.rails.append(row);
  }
}

function drawFindings(findings) {
  els.findings.innerHTML = "";
  show(els.findingsBlock, findings.length > 0);
  for (const finding of findings) {
    const item = document.createElement("li");
    item.className = `f-${finding.severity}`;
    item.innerHTML = `
      <span class="glyph">${GLYPH[finding.severity]}</span>
      <span>
        <span class="title">${escapeHtml(finding.title)}</span>
        ${finding.fix ? `<span class="fix">${escapeHtml(finding.fix)}</span>` : ""}
      </span>
      <span class="strength">${pct(finding.strength)}</span>`;
    els.findings.append(item);
  }
}

function drawMarkup(draft, marked) {
  show(els.markupBlock, marked.length > 0);
  if (!marked.length) return;
  els.sentenceNote.textContent =
    `${marked.length} sentences, all asked about in one request`;

  // Walk the draft once, wrapping each flagged sentence where Jev found it.
  let html = "";
  let cursor = 0;
  const used = new Set();
  for (const sentence of marked) {
    if (!sentence.probe || sentence.start < cursor) continue;
    used.add(sentence.probe);
    const detail = Object.entries(sentence.probes)
      .map(([name, value]) => `${PROBE_LABEL[name] || name}: ${pct(value)}`)
      .join(" · ");
    html += escapeHtml(draft.slice(cursor, sentence.start));
    html += `<mark class="m-${sentence.probe}" title="${escapeHtml(detail)}">` +
      `${escapeHtml(draft.slice(sentence.start, sentence.end))}</mark>`;
    cursor = sentence.end;
  }
  html += escapeHtml(draft.slice(cursor));
  els.marked.innerHTML = html;

  els.legend.innerHTML = "";
  for (const probe of used) {
    const entry = document.createElement("span");
    entry.innerHTML =
      `<i class="m-${probe}"></i> ${escapeHtml(PROBE_LABEL[probe] || probe)}`;
    els.legend.append(entry);
  }
}

function drawCost(cost, rescored) {
  if (rescored) {
    els.cost.textContent =
      `re-scored in code · 0 requests to Jev · the measurements below are ` +
      `the same ones from the read above`;
    return;
  }
  const plural = cost.requests === 1 ? "request" : "requests";
  els.cost.textContent =
    `${cost.questions} questions in ${cost.requests} ${plural} · ` +
    `${cost.inputTokens} input tokens / ${cost.outputTokens} output`;
}

function drawPills(activeKey) {
  els.pills.innerHTML = "";
  for (const audience of config.audiences) {
    const pill = document.createElement("button");
    pill.type = "button";
    pill.className = "pill";
    pill.textContent = audience.label;
    pill.setAttribute("aria-pressed", String(audience.key === activeKey));
    pill.addEventListener("click", () => rescore(audience.key));
    els.pills.append(pill);
  }
}

function render(data, { rescored = false } = {}) {
  current = data;
  if (data.sentences.length) sentences = data.sentences;
  drawVerdict(data);
  drawPills(data.audience.key);
  drawRails(data.rails, data.audience.label);
  drawFindings(data.findings);
  drawMarkup(data.draft, sentences);
  drawCost(data.cost, rescored);
  show(els.result, true);

  els.rescoreNote.textContent = rescored
    ? "same numbers, different reader — no model call"
    : "";
  if (rescored) {
    els.rescoreNote.classList.remove("flash");
    void els.rescoreNote.offsetWidth;   // restart the animation
    els.rescoreNote.classList.add("flash");
  }
}

/* ----------------------------------------------------------- requests */

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

async function read(event) {
  event?.preventDefault();
  const draft = els.draft.value.trim();
  if (!draft) return;

  show(els.error, false);
  show(els.result, false);
  show(els.thinking, true);
  els.thinkingText.textContent = els.deep.checked
    ? "reading the draft, then every sentence in it…"
    : "reading the draft…";
  els.send.disabled = true;
  sentences = [];

  try {
    const data = await post("/api/read", {
      draft,
      to: els.to.value.trim() || null,
      goal: els.goal.value.trim() || null,
      channel: els.channel.value || null,
      deep: els.deep.checked,
    });
    render(data);
  } catch (error) {
    els.error.textContent = error.message;
    show(els.error, true);
  } finally {
    show(els.thinking, false);
    els.send.disabled = false;
  }
}

async function rescore(audienceKey) {
  if (!current || audienceKey === current.audience.key) return;
  try {
    const data = await post("/api/rescore", {
      measurement: current.measurement,
      audience: audienceKey,
    });
    render(data, { rescored: true });
  } catch (error) {
    els.error.textContent = error.message;
    show(els.error, true);
  }
}

/* ----------------------------------------------------------- wiring */

function fillSample() {
  const sample = config.samples[sampleIndex % config.samples.length];
  sampleIndex += 1;
  els.draft.value = sample.draft;
  els.to.value = sample.to || "";
  els.goal.value = sample.goal || "";
  els.channel.value = [...els.channel.options].some((o) => o.value === sample.channel)
    ? sample.channel
    : "";
  els.draft.dispatchEvent(new Event("input"));
  els.draft.focus();
}

els.form.addEventListener("submit", read);
els.sample.addEventListener("click", fillSample);

els.draft.addEventListener("input", () => {
  els.charcount.textContent = `${els.draft.value.length} characters`;
});

document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") read(event);
});

fetch("/api/desk")
  .then((response) => response.json())
  .then((data) => { config = data; });
