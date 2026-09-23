/* How Jev read the repo's labels: the families it built questions from,
 * each label's role with its confidence, and what got no question and why. */

import type { RepoResult } from "../api.js";
import { h } from "../dom.js";
import { dollars, meter, two } from "../format.js";

export function taxonomyPanel(result: RepoResult) {
  const { repo, taxonomy } = result;
  const r = taxonomy.reading;
  const color = new Map(repo.labels.map((l) => [l.name, l.color]));
  const swatch = (name: string) =>
    h("span", { class: "swatch", style: `background:#${color.get(name) || "555"}` });

  const why = new Map<string, string[]>();
  for (const [name, reason] of Object.entries(taxonomy.ignored)) {
    why.set(reason, [...(why.get(reason) ?? []), name]);
  }
  const roles = Object.entries(taxonomy.roles).sort(
    (a, b) => a[1].role.localeCompare(b[1].role) || b[1].issues - a[1].issues,
  );

  return h(
    "div",
    { class: "taxonomy" },
    h("p", { class: "lede" },
      `Before any issue, Jev reads the ${Object.keys(taxonomy.roles).length} labels this repo has used on issues — `,
      "one Choice each, ‘what role does this label play?’ — and code turns the answers into the questions every triage asks.",
      r ? h("span", { class: "faint" }, ` One request · ${r.input_tokens.toLocaleString()} tokens · ${dollars(r.cost_usd)} · ${r.latency_s.toFixed(2)}s.`) : null,
    ),
    h("div", { class: "families" },
      taxonomy.families.map((f) =>
        h("div", { class: "family" },
          h("div", { class: "family-head" }, h("strong", null, f.title), h("span", { class: "faint" }, f.mode === "choice" ? "one Choice" : "a Noul per label")),
          h("div", { class: "chips" }, f.labels.map((n) => h("span", { class: "chip existing", title: f.descriptions[n] || n }, swatch(n), n))),
        ),
      ),
    ),
    h("details", null,
      h("summary", null, "every label's role"),
      h("div", { class: "roles" },
        roles.map(([name, info]) =>
          h("div", { class: "role-row" },
            h("span", { class: "role-name" }, swatch(name), name),
            h("span", { class: "role" }, info.role.replace(/_/g, " ")),
            meter(info.confidence),
            h("span", { class: "dist-value" }, two(info.confidence)),
          ),
        ),
      ),
    ),
    why.size
      ? h("details", null,
          h("summary", null, `no question asked (${Object.keys(taxonomy.ignored).length})`),
          ...[...why.entries()].map(([reason, names]) =>
            h("p", { class: "small" }, h("strong", null, `${reason}: `), names.join(", "))),
        )
      : null,
  );
}
