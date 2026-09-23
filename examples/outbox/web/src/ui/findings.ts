/* The findings list: severity glyph, headline, fix, and how strongly it holds. */

import type { Finding } from "../api.js";
import { escapeHtml, show } from "../dom.js";
import { result as els } from "../elements.js";
import { GLYPH, pct } from "../format.js";

function findingItem(finding: Finding): HTMLLIElement {
  const item = document.createElement("li");
  item.className = `f-${finding.severity}`;
  item.innerHTML = `
      <span class="glyph">${GLYPH[finding.severity]}</span>
      <span>
        <span class="title">${escapeHtml(finding.title)}</span>
        ${finding.fix ? `<span class="fix">${escapeHtml(finding.fix)}</span>` : ""}
      </span>
      <span class="strength">${pct(finding.strength)}</span>`;
  return item;
}

export function drawFindings(findings: Finding[]): void {
  show(els.findingsBlock, findings.length > 0);
  els.findings.replaceChildren(...findings.map(findingItem));
}
