from triage.clean import clean_text, human_comments, split
from triage.github import Comment, Issue


def test_spans_point_at_the_exact_text():
    body = clean_text(
        "First sentence. Second one!\n\n- a list item\n\nThird, e.g. with an abbreviation."
    )
    for unit in split(body):
        assert body[unit.start : unit.end] == unit.text


def test_units_are_sentences_items_and_headings():
    units = split("### Steps\nIt breaks. Every time.\n- run `x`\n")
    assert [(u.kind, u.text) for u in units] == [
        ("heading", "### Steps"),
        ("sentence", "It breaks."),
        ("sentence", "Every time."),
        ("item", "- run `x`"),
    ]
    assert not units[0].asked


def test_a_code_block_is_one_unit_and_long_ones_are_shortened():
    trace = "\n".join(f"frame {i}" for i in range(60))
    body = clean_text(f"It crashed:\n```\n{trace}\n```\nThat's all.")
    units = split(body)
    code = [u for u in units if u.kind == "code"]
    assert len(code) == 1
    assert "lines omitted" in code[0].text
    assert "frame 0" in code[0].text and "frame 59" in code[0].text


def test_template_noise_is_removed():
    body = clean_text(
        "<!-- please fill in -->\n### Logs\n_No response_\n- [ ] I searched\nReal text."
    )
    assert "please fill" not in body
    assert "No response" not in body
    assert "[ ]" not in body
    assert "Real text." in body


def test_bot_comments_never_reach_the_state():
    issue = Issue(
        number=1,
        title="t",
        body="b",
        state="OPEN",
        url="",
        author="reporter",
        association="NONE",
        created_at="",
        comments=[
            Comment("github-actions", "CONTRIBUTOR", "Priority: P2", "", is_bot=True),
            Comment("reporter", "NONE", "Still happens on 1.2", ""),
            Comment("maint", "MEMBER", "Can you share logs?", ""),
        ],
    )
    thread = human_comments(issue)
    assert [c["from"] for c in thread] == ["reporter", "maintainer"]
    assert all("Priority" not in c["text"] for c in thread)
