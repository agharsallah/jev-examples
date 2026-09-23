"""Terminal output. Every number shown is one Jev returned or code computed."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .policy import LANES, Assessment
from .taxonomy import Taxonomy

console = Console()

LANE_STYLE = {
    "private": "bold white on red",
    "human": "bold black on yellow",
    "close": "bold white on grey42",
    "duplicate": "bold white on dark_orange3",
    "needs_info": "bold black on khaki1",
    "auto": "bold black on green",
    "confirm": "bold black on pale_green3",
}
STATUS_STYLE = {"apply": "green", "confirm": "yellow", "unsure": "grey50"}


def banner() -> None:
    console.print(
        Text("triage", style="bold") + Text("  · Jev reads the issue, code decides", style="dim")
    )


def bar(p: float, width: int = 20) -> Text:
    filled = round(max(0.0, min(1.0, p)) * width)
    return Text("█" * filled, style="cyan") + Text("·" * (width - filled), style="grey30")


def taxonomy_report(tax: Taxonomy) -> None:
    table = Table(
        title=f"How Jev read the labels of {tax.repo}",
        title_justify="left",
        show_edge=False,
        pad_edge=False,
    )
    table.add_column("family")
    table.add_column("asked as")
    table.add_column("labels")
    for family in tax.families:
        table.add_row(
            family.title,
            "one Choice" if family.mode == "choice" else "a Noul each",
            ", ".join(family.labels),
        )
    console.print(table)

    roles = Table(show_edge=False, pad_edge=False, title="Role of each label", title_justify="left")
    roles.add_column("label")
    roles.add_column("role")
    roles.add_column("confidence", justify="right")
    roles.add_column("")
    for name, info in sorted(tax.roles.items(), key=lambda kv: (kv[1]["role"], -kv[1]["issues"])):
        roles.add_row(name, info["role"], f"{info['confidence']:.2f}", bar(info["confidence"], 12))
    console.print(roles)

    if tax.ignored:
        why: dict[str, list[str]] = {}
        for name, reason in tax.ignored.items():
            why.setdefault(reason, []).append(name)
        lines = [
            Text.assemble((reason, "bold"), ": ", ", ".join(names)) for reason, names in why.items()
        ]
        console.print(
            Panel(
                Group(*lines), title="No question asked", title_align="left", border_style="grey42"
            )
        )
    if tax.reading:
        r = tax.reading
        cached = " · cached" if r["cached"] else ""
        console.print(
            f"[dim]{len(tax.roles)} labels in one request · {r['input_tokens']:,} tokens · "
            f"${r['cost_usd']:.4f} · {r['latency_s']:.2f}s{cached}[/dim]"
        )


def issue_report(m: dict, a: Assessment, *, trace: bool = True) -> None:
    issue, answers = m["issue"], m["answers"]
    console.print()
    console.print(Text.assemble((f"#{issue['number']} ", "bold"), issue["title"]))
    console.print(f"[dim]{issue['url']}[/dim]")
    lanes = Text()
    for lane in a.lanes:
        lanes += Text(f" {LANES[lane]} ", style=LANE_STYLE[lane]) + Text(" ")
    console.print(lanes)

    kind = answers["kind"]
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column()
    grid.add_column(justify="right")
    for option, p in sorted(kind["probabilities"].items(), key=lambda kv: -kv[1])[:3]:
        grid.add_row(
            "kind" if option == kind["choice"] else "", Text(option) + " " + bar(p), f"{p:.2f}"
        )
    grid.add_row("", Text(f"confidence {kind['confidence']:.2f}", style="dim"), "")
    for name in ("impact", "clarity", "actionability", "scope", "frustration"):
        s = answers[name]
        grid.add_row(
            name, bar(s["score"] / (s["levels"] - 1)), f"{s['score']:.2f}/{s['levels'] - 1}"
        )
    grid.add_row("priority", bar(a.priority), f"{a.priority:.2f}")
    console.print(Panel(grid, title="What Jev read", title_align="left", border_style="cyan"))

    labels = Table(show_edge=False, pad_edge=False)
    labels.add_column("suggested label")
    labels.add_column("family")
    labels.add_column("p", justify="right")
    labels.add_column("")
    for label in a.labels:
        on = "  (already on it)" if label["label"] in issue["labels"] else ""
        labels.add_row(
            Text(label["label"] + on, style=STATUS_STYLE[label["status"]]),
            label["family"],
            f"{label['p']:.2f}",
            label["status"],
        )
    console.print(labels)
    console.print(f"[dim]labels on the issue now: {', '.join(issue['labels']) or 'none'}[/dim]")
    for d in a.drift:
        console.print(
            f"[yellow]label drift[/yellow] {d['family']}: on it is [bold]{d['current']}[/bold] "
            f"(p {d['p_current']:.2f}); Jev reads [bold]{d['suggested']}[/bold] "
            f"(p {d['p_suggested']:.2f})"
        )

    if a.duplicates:
        dup = Table(title="Duplicate check", title_justify="left", show_edge=False, pad_edge=False)
        dup.add_column("#", justify="right")
        dup.add_column("candidate", no_wrap=True, overflow="ellipsis")
        dup.add_column("same problem", justify="right")
        dup.add_column("related", justify="right")
        dup.add_column("")
        for d in a.duplicates:
            style = {"duplicate": "bold red", "related": "yellow"}.get(d["verdict"], "grey50")
            dup.add_row(
                str(d["number"]),
                d["title"][:64],
                f"{d['same']:.2f}",
                f"{d['related']:.2f}",
                Text(d["verdict"], style=style),
            )
        console.print(dup)

    units = {u["index"]: u for u in m["units"]}
    top = [e for e in a.evidence.get("kind", []) if e["p_target"] >= 0.6][:4]
    if top:
        lines = [
            Text.assemble((f"{e['p_target']:.2f} ", "cyan"), units[e["index"]]["text"][:110])
            for e in top
        ]
        console.print(
            Panel(
                Group(*lines),
                title=f"Why '{answers['kind']['choice']}': the strongest evidence",
                title_align="left",
                border_style="grey42",
            )
        )
    if a.reply:
        console.print(
            Panel(a.reply, title="Suggested reply (assembled from fixed lines)", title_align="left")
        )

    if trace:
        t = Table(
            title="Policy trace — plain Python over the numbers",
            title_justify="left",
            show_edge=False,
            pad_edge=False,
        )
        t.add_column("rule")
        t.add_column("value", justify="right")
        t.add_column("threshold", justify="right")
        t.add_column("fired")
        t.add_column("", style="dim")
        for rule in a.trace:
            value = f"{rule.value:.2f}" if isinstance(rule.value, float) else str(rule.value)
            t.add_row(
                rule.rule,
                value,
                str(rule.threshold or ""),
                Text("yes" if rule.fired else "no", style="bold" if rule.fired else "grey50"),
                rule.note,
            )
        console.print(t)

    u = m["usage"]
    cached = " · cached" if u["cached"] else ""
    console.print(
        f"[dim]{u['questions']} questions in one request · {u['input_tokens']:,} tokens · "
        f"${u['cost_usd']:.4f} · {u['latency_s']:.2f}s · {u['model']}{cached}[/dim]"
    )


def _totals_line(t: dict) -> str:
    fresh = f"{t['fresh_requests']} fresh" if t["fresh_requests"] != t["requests"] else "all fresh"
    extra = f" · {t['defanged']} sent with code/links softened" if t.get("defanged") else ""
    skipped = f" · {len(t['skipped'])} refused" if t.get("skipped") else ""
    return (
        f"[dim]{t['requests']} requests ({fresh}) · {t['questions']:,} questions · "
        f"{t['input_tokens']:,} tokens · ${t['cost_usd']:.3f} · {t['wall_s']:.1f}s wall · "
        f"{t['mean_latency_s']:.2f}s per request{extra}{skipped}[/dim]"
    )


def scan_report(result: dict) -> None:
    rows = sorted(result["rows"], key=lambda r: -r["assessment"]["priority"])
    by_lane: dict[str, list[dict]] = {}
    for row in rows:
        by_lane.setdefault(row["assessment"]["lane"], []).append(row)
    console.print(f"\n[bold]{result['repo']}[/bold] · {len(rows)} open issues read")
    for lane in LANES:
        items = by_lane.get(lane)
        if not items:
            continue
        table = Table(
            title=Text(f" {LANES[lane]} · {len(items)} ", style=LANE_STYLE[lane]),
            title_justify="left",
            show_edge=False,
            pad_edge=False,
            show_header=False,
        )
        table.add_column("#", justify="right", style="bold", no_wrap=True)
        table.add_column("title", no_wrap=True, overflow="ellipsis", ratio=3)
        table.add_column("kind", no_wrap=True)
        table.add_column("priority", justify="right", no_wrap=True)
        table.add_column("suggested", no_wrap=True, overflow="ellipsis", ratio=2)
        for row in items[:12]:
            a = row["assessment"]
            new = [
                lab["label"]
                for lab in a["labels"]
                if lab["status"] != "unsure" and lab["label"] not in row["labels"]
            ]
            notes = []
            if a["drift"]:
                notes.append(f"drift: {a['drift'][0]['current']}→{a['drift'][0]['suggested']}")
            if a["duplicates"] and a["duplicates"][0]["verdict"] == "duplicate":
                notes.append(f"dup of #{a['duplicates'][0]['number']}")
            table.add_row(
                str(row["number"]),
                row["title"][:70],
                f"{row['kind']} {row['kind_confidence']:.2f}",
                f"{a['priority']:.2f}",
                ", ".join(new + notes)[:60],
            )
        if len(items) > 12:
            table.add_row("", f"[dim]… {len(items) - 12} more[/dim]", "", "", "")
        console.print(table)
        console.print()
    console.print(_totals_line(result["totals"]))


def eval_report(report: dict) -> None:
    console.print(
        f"\n[bold]{report['repo']}[/bold] · agreement with the labels already on issues "
        "[dim](labels hidden from Jev)[/dim]\n"
    )
    for f in report["families"]:
        head = Table.grid(padding=(0, 3))
        for _ in range(5):
            head.add_column()
        f1 = f"{f['macro_f1']:.2f}" if f["macro_f1"] is not None else "—"
        head.add_row(
            Text(f["family"], style="bold"),
            f"n [bold]{f['n']}[/bold]",
            f"agree [bold]{f['agreement']:.0%}[/bold]",
            f"top-2 {f['top2']:.0%}",
            f"macro-F1 {f1} · ECE {f['ece']:.3f}",
        )
        console.print(head)
        cov = [c for c in f["coverage"] if c["threshold"] in (0.0, 0.5, 0.7, 0.8, 0.9)]
        line = "   auto-apply at " + "  ".join(
            f"{c['threshold']:.1f}: {c['coverage']:.0%} covered"
            + (f" @ {c['accuracy']:.0%}" if c["accuracy"] is not None else "")
            for c in cov
        )
        console.print(f"[dim]{line}[/dim]")
        rel = " ".join(f"{x['mean_p']:.2f}→{x['accuracy']:.2f}({x['n']})" for x in f["reliability"])
        console.print(f"[dim]   calibration (said → was right): {rel}[/dim]")
        if f["confusions"]:
            c = f["confusions"][0]
            console.print(
                f"   most common disagreement: on it [bold]{c['truth']}[/bold], Jev reads "
                f"[bold]{c['pick']}[/bold] ×{c['n']} "
                f"[dim]({f['top_confusion_share']:.0%} of misses)[/dim]"
            )
        for d in f["disagreements"][:3]:
            console.print(
                f"[dim]   #{d['number']} {', '.join(d['truth'])} → {d['pick']} "
                f"(p {d['p']:.2f})  {d['title'][:60]}[/dim]"
            )
        console.print()
    console.print(_totals_line(report["totals"]))


def overview_report(
    result: dict, *, ready_at: float = 0.85, beginner_at: float = 0.70, dup_at: float = 0.75
) -> None:
    rows = result["rows"]
    blocked = {"private", "human", "needs_info", "duplicate", "close"}
    ready = sorted(
        (
            r
            for r in rows
            if r["readiness"] >= ready_at and r["needs_decision"] < 0.5 and r["lane"] not in blocked
        ),
        key=lambda r: -r["readiness"] * (0.6 + 0.4 * r["impact"]),
    )
    beginner = sorted(
        (
            r
            for r in rows
            if r["beginner"] >= beginner_at
            and r["needs_decision"] < 0.5
            and r["security"] < 0.5
            and r["lane"] not in {"private", "close", "duplicate"}
        ),
        key=lambda r: -r["beginner"],
    )
    decision = sorted(
        (r for r in rows if r["needs_decision"] >= 0.6),
        key=lambda r: -r["needs_decision"] * (0.5 + 0.5 * r["impact"]),
    )
    pairs: dict[tuple[int, int], dict] = {}
    for e in result["edges"]:
        if e["same"] >= dup_at:
            key = tuple(sorted((e["a"], e["b"])))
            if key not in pairs or pairs[key]["same"] < e["same"]:
                pairs[key] = e

    r = result["repo"]
    console.print(
        f"\n[bold]{r['slug']}[/bold] · {r['read']} of {r['open_issues']} open issues read\n"
    )
    grid = Table.grid(padding=(0, 3))
    for _ in range(5):
        grid.add_column()
    grid.add_row(
        f"[bold green]{len(ready)}[/bold green] ready to pick up",
        f"[bold cyan]{len(beginner)}[/bold cyan] good first issues",
        f"[bold magenta]{len(decision)}[/bold magenta] waiting on a decision",
        f"[bold]{sum('needs_info' in x['lanes'] for x in rows)}[/bold] ask the reporter",
        f"[bold dark_orange3]{len(pairs)}[/bold dark_orange3] duplicate pairs",
    )
    console.print(grid)

    def listing(title: str, items: list[dict], score: str) -> None:
        table = Table(title=title, title_justify="left", show_edge=False, pad_edge=False)
        table.add_column("#", justify="right", style="bold", no_wrap=True)
        table.add_column("title", no_wrap=True, overflow="ellipsis", max_width=72)
        table.add_column("kind", no_wrap=True)
        table.add_column(score, justify="right", no_wrap=True)
        table.add_column("impact", justify="right", no_wrap=True)
        for x in items[:8]:
            table.add_row(
                str(x["number"]), x["title"], x["kind"], f"{x[score]:.2f}", f"{x['impact']:.2f}"
            )
        console.print()
        console.print(table)

    listing("Ready to pick up", ready, "readiness")
    listing("Good first issues", beginner, "beginner")
    listing("Waiting on a decision", decision, "needs_decision")
    if pairs:
        table = Table(
            title="Likely duplicates", title_justify="left", show_edge=False, pad_edge=False
        )
        table.add_column("open", justify="right", style="bold", no_wrap=True)
        table.add_column("same as", justify="right", no_wrap=True)
        table.add_column("p", justify="right", no_wrap=True)
        table.add_column("title of the other", no_wrap=True, overflow="ellipsis", max_width=72)
        for e in sorted(pairs.values(), key=lambda e: -e["same"])[:12]:
            table.add_row(
                f"#{e['a']}", f"#{e['b']} ({e['b_state']})", f"{e['same']:.2f}", e["b_title"]
            )
        console.print()
        console.print(table)
    console.print()
    console.print(_totals_line(result["totals"]))
