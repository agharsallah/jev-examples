/* The right-hand column: every card is drawn from the measurement (what Jev
 * said) and the assessment (what the policy made of it). Rescoring redraws
 * the assessment parts; the measurement never changes. */
import { h } from "../dom.js";
import { dollars, distribution, meter, pct, two } from "../format.js";
const num = (s, key) => s[key];
function card(title, note, ...children) {
    return h("section", { class: "card" }, h("header", { class: "card-head" }, h("h3", null, title), note ? h("span", { class: "card-note" }, note) : null), ...children);
}
function copyButton(text, label) {
    const button = h("button", { class: "ghost small", type: "button" }, label);
    button.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(text);
            button.textContent = "copied";
        }
        catch {
            button.textContent = "copy failed";
        }
        setTimeout(() => (button.textContent = label), 1400);
    });
    return button;
}
// -- the verdict ---------------------------------------------------------
export function verdictCard(m, a, meta) {
    const onIssue = new Set(m.issue.labels);
    const add = a.labels.filter((l) => l.status !== "unsure" && !onIssue.has(l.label)).map((l) => l.label);
    const gh = add.length
        ? `gh issue edit ${m.issue.number} -R ${m.repo.slug} ${add.map((l) => `--add-label ${JSON.stringify(l)}`).join(" ")}`
        : null;
    return card("Verdict", "plain Python over the numbers", h("div", { class: "lanes" }, a.lanes.map((lane, i) => h("span", { class: `lane lane-${lane}${i ? " secondary" : ""}` }, meta.lanes[lane] ?? lane))), h("div", { class: "priority" }, h("span", { class: "eyebrow" }, "priority"), meter(a.priority, { tone: "t-lamp", label: `priority ${two(a.priority)}` }), h("span", { class: "big-number" }, two(a.priority))), h("div", { class: "eyebrow" }, "suggested labels"), h("div", { class: "chips" }, a.labels.length
        ? a.labels.map((l) => h("span", { class: `chip s-${l.status}${onIssue.has(l.label) ? " on" : ""}`, title: `${l.family} · p ${two(l.p)}${l.confidence !== null ? ` · confidence ${two(l.confidence)}` : ""} · ${l.status}` }, l.label, h("small", null, two(l.p)), onIssue.has(l.label) ? h("i", null, "✓ on it") : null))
        : h("span", { class: "faint" }, "none")), h("div", { class: "eyebrow" }, "on the issue now"), h("div", { class: "chips" }, m.issue.labels.length ? m.issue.labels.map((l) => h("span", { class: "chip existing" }, l)) : h("span", { class: "faint" }, "no labels")), a.drift.length
        ? h("div", { class: "drift" }, a.drift.map((d) => h("p", null, h("strong", null, "Label drift · "), `${d.family}: it carries `, h("code", null, d.current), ` (p ${two(d.p_current)}), Jev reads `, h("code", null, d.suggested), ` (p ${two(d.p_suggested)}).`)))
        : null, gh ? h("div", { class: "row" }, h("code", { class: "cmd" }, gh), copyButton(gh, "copy gh command")) : null, a.reply
        ? h("div", { class: "reply" }, h("div", { class: "eyebrow" }, "suggested reply — assembled from fixed lines, not generated"), h("pre", null, a.reply), copyButton(a.reply, "copy reply"))
        : null, h("p", { class: "faint small" }, "Read-only: nothing is ever written to GitHub."));
}
// -- what Jev read -------------------------------------------------------
function ladder(name, answer, levels) {
    const top = Math.max(1, answer.levels - 1);
    const nearest = levels[Math.round(answer.score)] ?? "";
    return h("div", { class: "ladder" }, h("div", { class: "ladder-head" }, h("span", { class: "dist-name" }, name), h("span", { class: "dist-value" }, `${two(answer.score)} / ${top}`)), h("div", { class: "ladder-track" }, levels.map((_, i) => h("span", { class: "rung", style: `left:${(i / top) * 100}%` })), h("span", { class: "ladder-dot", style: `left:${(answer.score / top) * 100}%` })), h("div", { class: "ladder-caption", title: levels.join("\n") }, nearest, h("span", { class: "faint" }, ` · confidence ${two(answer.confidence)}`)));
}
export function readingCard(m, meta, s) {
    const kind = m.answers.kind;
    const families = m.taxonomy.families.filter((f) => f.mode === "choice");
    const scores = Object.keys(meta.levels);
    return card("What Jev read", `${m.usage.questions} questions · one request`, h("div", { class: "block" }, h("h4", null, "kind of report ", h("span", { class: "faint" }, `confidence ${two(kind.confidence)}`)), distribution(kind.probabilities, kind.choice, { limit: 4 })), ...families.map((family) => {
        const answer = m.answers[`fam__${family.key}`];
        if (!answer)
            return null;
        return h("div", { class: "block" }, h("h4", null, `${family.title} — this repo's labels `, h("span", { class: answer.confidence >= num(s, "choice_apply") ? "ok" : "faint" }, `confidence ${two(answer.confidence)}`)), distribution(answer.probabilities, answer.choice, { limit: 4, names: { none_fit: "none fits" } }));
    }), h("div", { class: "block" }, h("h4", null, "scores — each on its own rubric"), ...scores.map((name) => {
        const answer = m.answers[name];
        return answer && answer.type === "score" ? ladder(name, answer, meta.levels[name] ?? []) : null;
    })));
}
// -- checklist -----------------------------------------------------------
const CHECK_WORDS = {
    has_repro_steps: "steps to reproduce",
    has_expected_vs_actual: "expected vs actual",
    has_environment: "version / environment",
    has_error_output: "error output",
    has_workaround: "a workaround",
    has_proposed_fix: "points at a cause or fix",
    multiple_problems: "several problems in one",
    security_sensitive: "security-sensitive",
    low_effort: "spam or low effort",
    steers_triage: "tries to steer triage",
    answered_in_thread: "answered in the thread",
    fixed_in_thread: "reported fixed",
    waiting_on_reporter: "waiting on the reporter",
    reporter_confirmed: "reporter says solved",
};
const RISKS = new Set(["multiple_problems", "security_sensitive", "low_effort", "steers_triage"]);
export function checklistCard(m, a, s) {
    const isBug = m.answers.kind.choice === "bug";
    const rows = Object.entries(CHECK_WORDS).map(([key, words]) => {
        const answer = m.answers[key];
        if (!answer)
            return null;
        const risk = RISKS.has(key);
        const bar = risk ? num(s, key === "security_sensitive" ? "security" : key === "steers_triage" ? "steer" : key === "low_effort" ? "low_effort" : "present") : num(s, "present");
        const missing = a.missing.includes(key);
        return h("div", { class: `check${missing ? " missing" : ""}${risk && answer.noul >= bar ? " risk" : ""}` }, h("span", { class: "check-name" }, words, missing ? h("em", null, " missing") : null), meter(answer.noul, { threshold: bar, tone: risk ? "t-bug" : "t-good" }), h("span", { class: "dist-value" }, two(answer.noul)));
    });
    return card("Checklist", isBug ? "the repro questions count: it reads as a bug" : "asked anyway; only bugs are held to the repro items", h("div", { class: "checks" }, rows));
}
// -- duplicates ----------------------------------------------------------
export function duplicatesCard(a, s) {
    if (!a.duplicates.length)
        return card("Duplicates", "no candidates found", h("p", { class: "faint" }, "Search found nothing close enough to ask about."));
    return card("Duplicates", "code finds candidates, Jev judges them", h("p", { class: "faint small" }, "Two questions per candidate — the same problem, or merely related. The difference is what a ‘may be related’ bot comment gets wrong."), h("div", { class: "dups" }, a.duplicates.map((d) => h("div", { class: `dup v-${d.verdict}` }, h("a", { href: d.url, target: "_blank", rel: "noopener" }, `#${d.number}`), h("span", { class: "dup-title", title: d.title }, d.title), h("span", { class: "dup-state" }, d.state), h("div", { class: "dup-bars" }, h("span", { class: "tiny" }, "same"), meter(d.same, { threshold: num(s, "dup_same"), tone: "t-bug" }), h("span", { class: "dist-value" }, two(d.same)), h("span", { class: "tiny" }, "related"), meter(d.related, { threshold: num(s, "dup_related"), tone: "t-feature" }), h("span", { class: "dist-value" }, two(d.related))), h("span", { class: `verdict-tag v-${d.verdict}` }, d.verdict)))));
}
// -- why: evidence and counterfactuals -----------------------------------
export function whyCard(m, a, results, busy, onTest) {
    const text = new Map(m.units.map((u) => [u.index, u.text]));
    const kind = m.answers.kind.choice;
    const top = (a.evidence.kind ?? []).filter((e) => e.p_target >= 0.6).slice(0, 4);
    return card("Why", "evidence, then a test of it", h("h4", null, `the parts that read as ‘${kind}’`), top.length
        ? h("ol", { class: "evidence" }, top.map((e) => h("li", null, h("span", { class: "dist-value" }, two(e.p_target)), " ", clip(text.get(e.index) ?? "", 140))))
        : h("p", { class: "faint" }, "No single part reads strongly as one kind; the call comes from the whole."), h("button", { class: "primary", type: "button", disabled: busy, onclick: onTest }, busy ? "asking again…" : "Test it: remove the evidence and re-ask"), results ? counterfactualTable(m, results, text) : null);
}
function clip(s, n) {
    return s.length > n ? `${s.slice(0, n)}…` : s;
}
function counterfactualTable(m, results, text) {
    const keys = ["kind", ...m.taxonomy.families.filter((f) => f.mode === "choice").map((f) => `fam__${f.key}`), "impact"];
    const titles = { kind: "kind", impact: "impact" };
    for (const f of m.taxonomy.families)
        titles[`fam__${f.key}`] = f.title;
    const describe = (removed) => removed.map((i) => (i === -1 ? "the title" : `“${clip(text.get(i) ?? `unit ${i}`, 60)}”`)).join(" + ");
    const biggest = Math.max(0, ...results.flatMap((r) => Object.entries(r.moves).filter(([k]) => k !== "impact").map(([, mv]) => Math.abs(mv.before - mv.after))));
    const verdict = biggest < 0.1
        ? "Robust: no single part carries the call — take the strongest evidence away and the answer holds."
        : biggest < 0.3
            ? "Leaning: some calls move when evidence is removed, none flips on its own."
            : "Hinges on specific text: removing it moves or flips a decision.";
    return h("div", { class: "cf" }, h("p", { class: "cf-verdict" }, verdict), h("div", { class: "cf-table" }, results.map((r) => h("div", { class: "cf-row" }, h("div", { class: "cf-removed" }, "without ", describe(r.removed)), h("div", { class: "cf-moves" }, keys.filter((k) => r.moves[k]).map((k) => {
        const mv = r.moves[k];
        const delta = mv.after - mv.before;
        const isScore = mv.target === "score";
        return h("span", { class: `move${mv.flipped ? " flipped" : ""}${Math.abs(delta) >= (isScore ? 0.3 : 0.1) ? " moved" : ""}` }, h("b", null, titles[k] ?? k), " ", isScore ? "" : `${mv.target} `, `${two(mv.before)} → ${two(mv.after)}`, mv.flipped ? h("em", null, ` now ${mv.now}`) : null);
    }))))), h("p", { class: "faint small" }, `${results.length} requests at once · ${dollars(results.reduce((t, r) => t + r.cost_usd, 0))}`));
}
// -- the trace -----------------------------------------------------------
export function traceCard(a) {
    return card("Policy trace", "every rule, the number it read, and whether it fired", h("table", { class: "trace" }, h("thead", null, h("tr", null, h("th", null, "rule"), h("th", null, "value"), h("th", null, "bar"), h("th", null, ""))), h("tbody", null, a.trace.map((r) => h("tr", { class: r.fired ? "fired" : "" }, h("td", null, r.rule, r.note ? h("small", null, r.note) : null), h("td", { class: "num" }, typeof r.value === "number" ? two(r.value) : String(r.value ?? "")), h("td", { class: "num" }, r.threshold === null ? "" : String(r.threshold)), h("td", null, r.fired ? "fired" : "—"))))));
}
// -- raw -----------------------------------------------------------------
export function rawCard(result) {
    const u = result.measurement.usage;
    const json = (value) => h("pre", { class: "json" }, JSON.stringify(value, null, 2));
    return card("The request, exactly", `${u.input_tokens.toLocaleString()} tokens · ${dollars(u.cost_usd)} · ${u.latency_s.toFixed(2)}s · ${u.model}${u.cached ? " · cached" : ""}`, h("p", { class: "faint small" }, "What was sent to Jev and what came back. Note what the state leaves out: the labels already on the issue, and every bot comment."), h("details", null, h("summary", null, "state"), json(result.request.state)), h("details", null, h("summary", null, `questions (${Object.keys(result.request.questions).length})`), json(result.request.questions)), h("details", null, h("summary", null, "answers"), json(result.measurement.answers)));
}
export function usageLine(m) {
    const u = m.usage;
    return `${u.questions} questions in one request · ${u.input_tokens.toLocaleString()} tokens · ${dollars(u.cost_usd)} · ${u.latency_s.toFixed(2)}s${u.cached ? " (cached)" : ""}`;
}
export { pct };
