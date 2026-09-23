/* The page: pick a repo (and an issue), read it once, then let the knobs move
 * the verdict without asking again. The URL hash holds the reference, so any
 * view can be linked: #owner/repo/123. */
import { api, overviewApi, queueApi } from "./api.js";
import { byId, fill, h } from "./dom.js";
import { checklistCard, duplicatesCard, rawCard, readingCard, traceCard, usageLine, verdictCard, whyCard, } from "./ui/cards.js";
import { controls } from "./ui/controls.js";
import { evaluationView } from "./ui/evaluation.js";
import { overviewView } from "./ui/overview.js";
import { queueBoard } from "./ui/queue.js";
import { drawSheet } from "./ui/sheet.js";
import { taxonomyPanel } from "./ui/taxonomy.js";
const el = {
    form: byId("go"),
    ref: byId("ref"),
    fresh: byId("fresh"),
    examples: byId("examples"),
    status: byId("status"),
    repoBar: byId("repoBar"),
    repoName: byId("repoName"),
    repoMeta: byId("repoMeta"),
    labelsToggle: byId("labelsToggle"),
    taxonomy: byId("taxonomy"),
    issueView: byId("issueView"),
    issueHead: byId("issueHead"),
    lens: byId("lens"),
    sheet: byId("sheet"),
    inspector: byId("inspector"),
    usage: byId("usage"),
    cards: byId("cards"),
    knobs: byId("knobs"),
    trace: byId("trace"),
    raw: byId("raw"),
    hint: byId("hint"),
    tabs: byId("tabs"),
    queueView: byId("queueView"),
    queueLimit: byId("queueLimit"),
    queueRun: byId("queueRun"),
    queueBoard: byId("queueBoard"),
    queueKnobs: byId("queueKnobs"),
    evalView: byId("evalView"),
    evalLimit: byId("evalLimit"),
    evalRun: byId("evalRun"),
    evalBody: byId("evalBody"),
    overviewView: byId("overviewView"),
    overviewRunRow: byId("overviewRunRow"),
    overviewIntro: byId("overviewIntro"),
    overviewLimit: byId("overviewLimit"),
    overviewRun: byId("overviewRun"),
    overviewProgress: byId("overviewProgress"),
    overviewSnapshot: byId("overviewSnapshot"),
    overviewAge: byId("overviewAge"),
    overviewRefresh: byId("overviewRefresh"),
    overviewBody: byId("overviewBody"),
};
const state = {
    meta: null,
    repo: null,
    issue: null,
    assessment: null,
    settings: null,
    lens: "kind",
    counterfactuals: null,
    asking: false,
    ref: "",
    view: "issue",
    scan: null,
    queueRows: null,
    evaluation: null,
    overview: null,
    knobs: { readyAt: 0.85, beginnerAt: 0.7, dupAt: 0.75 },
    filters: { flag: null, kind: null, component: null, quadrant: null, q: "" },
    sort: "readiness",
};
// -- status line ---------------------------------------------------------
function busy(text) {
    fill(el.status, h("span", { class: "spinner", "aria-hidden": "true" }), text);
    el.status.className = "status busy";
    el.status.hidden = false;
}
function failed(error) {
    fill(el.status, String(error instanceof Error ? error.message : error));
    el.status.className = "status error";
    el.status.hidden = false;
}
function idle() {
    el.status.hidden = true;
}
// -- references ----------------------------------------------------------
function parseRef(raw) {
    const match = raw
        .trim()
        .replace(/^https?:\/\/github\.com\//, "")
        .match(/^([\w.-]+)\/([\w.-]+?)(?:\.git)?(?:(?:\/issues\/|#|\/)(\d+|queue|eval|overview))?\/?$/);
    if (!match)
        return null;
    const tail = match[3];
    const number = tail && /^\d+$/.test(tail) ? Number(tail) : null;
    const view = tail === "queue" || tail === "eval" || tail === "overview" ? tail : number ? "issue" : null;
    return { repo: `${match[1]}/${match[2]}`, number, view };
}
function show(view) {
    state.view = view;
    el.tabs.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
    el.issueView.hidden = view !== "issue" || !state.issue;
    el.hint.hidden = view !== "issue" || !!state.issue;
    el.queueView.hidden = view !== "queue";
    el.overviewView.hidden = view !== "overview";
    el.evalView.hidden = view !== "eval";
}
function setHash(repo, tail) {
    history.replaceState(null, "", `#${repo}${tail !== null ? `/${tail}` : ""}`);
}
function refFromHash() {
    return decodeURIComponent(location.hash.replace(/^#/, ""));
}
// -- drawing -------------------------------------------------------------
function drawRepo() {
    const r = state.repo;
    if (!r)
        return;
    el.repoBar.hidden = false;
    fill(el.repoName, h("a", { href: r.repo.url, target: "_blank", rel: "noopener" }, r.repo.slug));
    const families = r.taxonomy.families.map((f) => f.title).join(" · ");
    fill(el.repoMeta, `${r.repo.open_issues.toLocaleString()} open issues · Jev built questions for: ${families || "no label families (built-in kinds only)"}`);
    fill(el.taxonomy, taxonomyPanel(r));
}
/** Once per issue: the parts that hold their own UI state (a slider mid-drag,
 * an open <details>) and do not depend on the verdict. */
function drawStatic() {
    const result = state.issue;
    if (!result || !state.meta || !state.settings)
        return;
    fill(el.knobs, controls(state.settings, state.meta.defaults, (s, reset) => void rescore(s, reset)));
    fill(el.raw, rawCard(result));
}
function drawIssue() {
    const result = state.issue;
    const a = state.assessment;
    const meta = state.meta;
    if (!result || !a || !meta || !state.settings)
        return;
    const m = result.measurement;
    el.issueView.hidden = state.view !== "issue";
    el.hint.hidden = true;
    fill(el.issueHead, state.overview
        ? h("button", { class: "ghost small back", type: "button", onclick: () => backToOverview() }, "← back to the overview")
        : null, h("div", { class: "eyebrow" }, h("a", { href: m.issue.url, target: "_blank", rel: "noopener" }, `${m.repo.slug}#${m.issue.number}`), ` · ${m.issue.state.toLowerCase()} · by ${m.issue.author} (${m.issue.association.toLowerCase()}) · ${m.issue.comments} comments`), h("h2", null, m.issue.title));
    drawSheet(el.sheet, m, a, state.lens, el.inspector, { onRemove: (units) => runCounterfactual([units]) });
    el.usage.textContent = usageLine(m);
    fill(el.cards, verdictCard(m, a, meta), whyCard(m, a, state.counterfactuals, state.asking, () => runCounterfactual(null)), readingCard(m, meta, state.settings), checklistCard(m, a, state.settings), duplicatesCard(a, state.settings));
    fill(el.trace, traceCard(a));
}
// -- actions -------------------------------------------------------------
async function rescore(settings, reset = false) {
    if (!state.issue)
        return;
    state.settings = structuredClone(settings);
    try {
        const { assessment } = await api.rescore(state.issue.measurement, state.settings);
        state.assessment = assessment;
        drawIssue();
        if (reset)
            drawStatic();
    }
    catch (error) {
        failed(error);
    }
}
async function runCounterfactual(removals) {
    if (!state.issue || !state.assessment || state.asking)
        return;
    const evidence = state.assessment.evidence.kind ?? [];
    const strong = evidence.filter((e) => e.p_target >= 0.6).slice(0, 3).map((e) => e.index);
    // The default test: the title, each strong unit alone, and all of them together.
    const plan = removals ?? [[-1], ...strong.map((i) => [i]), ...(strong.length > 1 ? [[-1, ...strong]] : [])];
    state.asking = true;
    drawIssue();
    try {
        const { results } = await api.counterfactual(state.ref, plan);
        state.counterfactuals = removals && state.counterfactuals ? [...results, ...state.counterfactuals] : results;
    }
    catch (error) {
        failed(error);
    }
    finally {
        state.asking = false;
        drawIssue();
        byId("cards").querySelector(".cf")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}
async function open(raw, fresh = false) {
    const parsed = parseRef(raw);
    if (!parsed) {
        failed("Try owner/repo, owner/repo#123, or an issue URL.");
        return;
    }
    const ref = parsed.number ? `${parsed.repo}#${parsed.number}` : parsed.repo;
    el.ref.value = ref;
    setHash(parsed.repo, parsed.number ?? (parsed.view === "issue" ? null : parsed.view));
    try {
        if (!state.repo || state.repo.repo.slug.toLowerCase() !== parsed.repo.toLowerCase()) {
            busy(`reading the labels of ${parsed.repo}…`);
            state.repo = await api.repo(parsed.repo);
            state.issue = null;
            state.scan = null;
            state.queueRows = null;
            state.evaluation = null;
            state.overview = null;
            el.overviewBody.replaceChildren();
            el.overviewRunRow.hidden = false;
            el.overviewSnapshot.hidden = true;
            el.queueBoard.replaceChildren();
            el.queueKnobs.replaceChildren();
            el.evalBody.replaceChildren();
            drawRepo();
            el.tabs.hidden = false;
        }
        state.settings ??= structuredClone(state.meta.defaults);
        if (!parsed.number) {
            // A repo on its own opens on the overview: the whole picture first.
            show(parsed.view ?? "overview");
            if (!parsed.view)
                setHash(parsed.repo, "overview");
            primeOverview();
            await loadSavedOverview();
            idle();
            return;
        }
        show("issue");
        busy(`reading #${parsed.number}: one request, every question…`);
        state.ref = ref;
        state.counterfactuals = null;
        state.issue = await api.issue(ref, fresh);
        const { assessment } = await api.rescore(state.issue.measurement, state.settings);
        state.assessment = assessment;
        idle();
        drawIssue();
        drawStatic();
        show("issue");
    }
    catch (error) {
        failed(error);
    }
}
// -- the overview ----------------------------------------------------------------
/** Show the saved overview if there is one. Opening the page reads a file on
 * the server and nothing else: no GitHub call, no Jev request. */
async function loadSavedOverview() {
    if (!state.repo || state.overview)
        return;
    const slug = state.repo.repo.slug;
    const found = await overviewApi.saved(slug).catch(() => null);
    if (!found || state.repo?.repo.slug !== slug)
        return;
    state.overview = found;
    drawOverview();
}
function ago(seconds) {
    const s = Math.max(0, Date.now() / 1000 - seconds);
    if (s < 90)
        return "just now";
    if (s < 3600)
        return `${Math.round(s / 60)} minutes ago`;
    if (s < 86400 * 2)
        return `${Math.round(s / 3600)} hours ago`;
    return `${Math.round(s / 86400)} days ago`;
}
function primeOverview() {
    if (!state.repo || state.overview)
        return;
    const open = state.repo.repo.open_issues;
    const n = Math.min(open, 1000);
    // Measured on omnigent: about $0.0003 and 0.4 s per issue, eight in flight.
    el.overviewIntro.textContent =
        `Every open issue, read once and laid out: what is ready, what a newcomer could take, what waits on a decision, ` +
            `which issues are the same problem twice. ${n.toLocaleString()} open issue${n === 1 ? "" : "s"} · ` +
            `about $${(n * 0.0003).toFixed(2)} and ${Math.max(5, Math.round((n * 0.4) / 8 + 5))} s the first time, free after that (cached).`;
}
function drawOverview() {
    if (!state.overview)
        return;
    el.overviewRunRow.hidden = true;
    const o = state.overview;
    const fresh = o.totals.fresh_requests;
    el.overviewSnapshot.hidden = false;
    el.overviewAge.textContent =
        `Read ${ago(o.saved_at)} · ${o.repo.read} issues · ` +
            (fresh ? `${fresh} new Jev request${fresh === 1 ? "" : "s"} that time` : "every answer from the cache that time") +
            ` · shown from the saved copy: nothing is re-read until you refresh.`;
    el.overviewBody.replaceChildren(overviewView(state.overview, state.knobs, state.filters, state.sort, {
        open: openIssue,
        filter: (patch) => {
            state.filters = { ...state.filters, ...patch };
            const focused = document.activeElement;
            const typing = focused?.type === "search";
            drawOverview();
            if (typing) {
                const search = el.overviewBody.querySelector('input[type="search"]');
                search?.focus();
                search?.setSelectionRange(search.value.length, search.value.length);
            }
        },
        knobs: (patch) => {
            state.knobs = { ...state.knobs, ...patch };
            drawOverview();
        },
        sort: (key) => {
            state.sort = key;
            drawOverview();
        },
    }));
}
async function runOverview(refresh = false) {
    if (!state.repo)
        return;
    const raw = el.overviewLimit.value.trim();
    const limit = raw ? Number(raw) : (state.overview?.limit ?? null);
    el.overviewRun.disabled = true;
    el.overviewRefresh.disabled = true;
    el.overviewProgress.hidden = false;
    const fill = el.overviewProgress.querySelector(".progress-fill");
    const text = el.overviewProgress.querySelector("span");
    text.textContent = refresh ? "fetching the open issues from GitHub again…" : "reading the open issues…";
    fill.style.width = "0%";
    try {
        const { job } = await overviewApi.start(state.repo.repo.slug, limit, refresh);
        for (;;) {
            await new Promise((r) => setTimeout(r, 700));
            const status = await overviewApi.poll(job);
            if (status.total) {
                fill.style.width = `${(status.done / status.total) * 100}%`;
                text.textContent = `read ${status.done} of ${status.total} issues`;
            }
            if (status.status === "failed")
                throw new Error(status.error ?? "The overview failed.");
            if (status.status === "done" && status.result) {
                state.overview = status.result;
                break;
            }
        }
        el.overviewProgress.hidden = true;
        drawOverview();
    }
    catch (error) {
        el.overviewProgress.hidden = true;
        failed(error);
    }
    finally {
        el.overviewRun.disabled = false;
        el.overviewRefresh.disabled = false;
    }
}
// -- the queue and the evaluation -------------------------------------------
function backToOverview() {
    if (!state.repo)
        return;
    show("overview");
    setHash(state.repo.repo.slug, "overview");
}
function openIssue(number) {
    if (!state.repo)
        return;
    void open(`${state.repo.repo.slug}#${number}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
}
function drawQueue() {
    if (!state.scan || !state.queueRows || !state.meta)
        return;
    el.queueBoard.replaceChildren(queueBoard(state.scan, state.queueRows, state.meta.lanes, openIssue));
}
async function runQueue() {
    if (!state.repo || !state.settings)
        return;
    const limit = Number(el.queueLimit.value) || 60;
    el.queueRun.disabled = true;
    busy(`reading ${limit} open issues — one request each, eight in flight…`);
    try {
        state.scan = await queueApi.scan(state.repo.repo.slug, limit, state.settings);
        state.queueRows = state.scan.rows;
        idle();
        drawQueue();
        el.queueKnobs.replaceChildren(controls(state.settings, state.meta.defaults, (settings, reset) => void rescoreQueue(settings, reset)));
    }
    catch (error) {
        failed(error);
    }
    finally {
        el.queueRun.disabled = false;
    }
}
async function rescoreQueue(settings, reset = false) {
    if (!state.scan)
        return;
    state.settings = structuredClone(settings);
    try {
        const { rows } = await queueApi.rescore(state.scan.measurements, state.scan.taxonomy, state.settings);
        state.queueRows = rows;
        drawQueue();
        if (reset) {
            el.queueKnobs.replaceChildren(controls(state.settings, state.meta.defaults, (s, r) => void rescoreQueue(s, r)));
        }
    }
    catch (error) {
        failed(error);
    }
}
async function runEval() {
    if (!state.repo)
        return;
    const limit = Number(el.evalLimit.value) || 100;
    el.evalRun.disabled = true;
    busy(`triaging ${limit} labelled issues with their labels hidden…`);
    try {
        state.evaluation = await queueApi.evaluate(state.repo.repo.slug, limit);
        idle();
        const applyAt = state.settings?.choice_apply ?? 0.7;
        el.evalBody.replaceChildren(evaluationView(state.evaluation, applyAt, openIssue));
    }
    catch (error) {
        failed(error);
    }
    finally {
        el.evalRun.disabled = false;
    }
}
// -- wiring --------------------------------------------------------------
el.form.addEventListener("submit", (event) => {
    event.preventDefault();
    void open(el.ref.value, el.fresh.checked);
});
el.tabs.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-view]");
    if (!button || !state.repo)
        return;
    const view = button.dataset.view;
    show(view);
    const slug = state.repo.repo.slug;
    setHash(slug, view === "issue" ? (state.issue?.measurement.issue.number ?? null) : view);
});
el.queueRun.addEventListener("click", () => void runQueue());
el.overviewRun.addEventListener("click", () => void runOverview());
el.overviewRefresh.addEventListener("click", () => void runOverview(true));
el.evalRun.addEventListener("click", () => void runEval());
el.labelsToggle.addEventListener("click", () => {
    el.taxonomy.hidden = !el.taxonomy.hidden;
    el.labelsToggle.textContent = el.taxonomy.hidden ? "how Jev read the labels" : "hide the labels";
});
el.lens.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-lens]");
    if (!button)
        return;
    state.lens = button.dataset.lens;
    el.lens.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b === button));
    drawIssue();
});
window.addEventListener("hashchange", () => {
    const ref = refFromHash();
    if (ref)
        void open(ref);
});
async function start() {
    try {
        state.meta = await api.meta();
    }
    catch (error) {
        failed(error);
        return;
    }
    fill(el.examples, "try ", state.meta.examples.flatMap((ref, i) => [
        i ? " · " : "",
        h("button", { class: "link", type: "button", onclick: () => void open(ref) }, ref),
    ]));
    const ref = refFromHash();
    if (ref)
        void open(ref);
}
void start();
