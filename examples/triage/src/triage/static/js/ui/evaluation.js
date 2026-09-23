/* The evaluation: agreement with the labels people already put on issues,
 * with those labels hidden from Jev. Calibration is the headline, because it
 * is what makes a threshold mean anything. */
import { h } from "../dom.js";
import { dollars, githubLink, pct, two } from "../format.js";
import { confusionTable, coverageChart, reliabilityChart } from "./charts.js";
export function evaluationView(report, applyAt, onOpen) {
    const t = report.totals;
    return h("div", { class: "evaluation" }, h("p", { class: "lede" }, `${t.issues} recent issues that already carry labels were triaged with those labels hidden from Jev, `, "and each label family's Choice compared to what is on the issue. ", h("strong", null, "Agreement, not accuracy: "), "the labels on the issues are someone's judgment too — on some repos, another bot's — so a disagreement is as likely to be a mislabelled issue as a model mistake.", h("span", { class: "faint" }, ` ${t.questions.toLocaleString()} questions · ${t.input_tokens.toLocaleString()} tokens · ${dollars(t.cost_usd)} · ${t.mean_latency_s.toFixed(2)}s per issue.`)), report.families.map((f) => familyCard(f, applyAt, onOpen)));
}
function familyCard(f, applyAt, onOpen) {
    const at = f.coverage.reduce((best, c) => (Math.abs(c.threshold - applyAt) < Math.abs(best.threshold - applyAt) ? c : best), f.coverage[0]);
    const top = f.confusions[0];
    const calibrated = f.ece < 0.05 ? "well calibrated" : f.ece < 0.12 ? "roughly calibrated" : "overconfident here";
    return h("section", { class: "card eval-card" }, h("header", { class: "card-head" }, h("h3", null, f.family), h("span", { class: "card-note" }, `${f.n} labelled issues`)), h("div", { class: "eval-stats" }, big(pct(f.agreement), "agree with the label on the issue"), big(pct(f.top2), "have it in Jev's top two"), big(two(f.ece), `calibration error · ${calibrated}`), big(`${pct(at.coverage)}`, `auto-labelled at ≥ ${two(at.threshold)}, ${at.accuracy === null ? "—" : pct(at.accuracy)} of them agree`)), h("div", { class: "eval-charts" }, h("figure", null, h("figcaption", null, "Calibration — when Jev says p, is it right p of the time? Dots on the diagonal are calibrated; dot size is issue count."), reliabilityChart(f.reliability)), h("figure", null, h("figcaption", null, "The auto-apply knob — raise the bar, fewer issues clear it, more of those agree."), coverageChart(f.coverage, applyAt))), top
        ? h("p", { class: "insight" }, h("strong", null, "Most common disagreement: "), "on the issue ", h("code", null, top.truth), ", Jev reads ", h("code", null, top.pick), ` — ${top.n}×, ${pct(f.top_confusion_share)} of the misses. `, f.top_confusion_share >= 0.35
            ? "When one pair dominates, read the two label descriptions side by side: often nothing in an issue's text could tell them apart."
            : "")
        : null, h("details", null, h("summary", null, "confusion matrix"), confusionTable(f.confusion.labels, f.confusion.cells, { none_fit: "none fits" })), f.disagreements.length
        ? h("details", null, h("summary", null, `where it disagrees most confidently (${f.disagreements.length})`), h("ol", { class: "disagree" }, f.disagreements.map((d) => h("li", null, h("button", { class: "link", type: "button", onclick: () => onOpen(d.number) }, `#${d.number}`), " ", h("span", null, d.title), " ", githubLink(d.url, "↗"), " ", h("span", { class: "faint" }, `on it ${d.truth.join(", ")} (p ${two(d.p_truth)}) · Jev ${d.pick} (p ${two(d.p)})`)))))
        : null);
}
function big(value, label) {
    return h("div", { class: "stat" }, h("strong", null, value), h("span", null, label));
}
