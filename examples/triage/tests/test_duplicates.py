from triage.duplicates import BM25, shortlist, words
from triage.github import Issue


def _issue(number, title, body=""):
    return Issue(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url="",
        author="a",
        association="NONE",
        created_at="",
    )


CORPUS = [
    _issue(1, "Login page crashes on Safari", "TypeError in auth.js when clicking login"),
    _issue(2, "Add dark mode to settings"),
    _issue(3, "Export to CSV drops unicode characters"),
    _issue(4, "Safari: login button does nothing", "auth.js throws TypeError"),
]


def test_stopwords_and_short_words_are_dropped():
    assert words("The bug is that it crashes") == ["crashes"]


def test_bm25_finds_the_neighbour_and_never_the_issue_itself():
    ranked = BM25(CORPUS).rank(words("login crashes safari auth.js typeerror"), exclude=1, top=3)
    assert ranked[0][0].number == 4
    assert all(issue.number != 1 for issue, _ in ranked)


def test_distinctive_words_are_the_rare_ones():
    index = BM25(CORPUS)
    assert index.distinctive(_issue(9, "Export unicode login"), 1) in (["export"], ["unicode"])


def test_shortlist_without_search_is_local_only():
    found = shortlist("o/r", CORPUS[0], CORPUS, search=False)
    assert found[0].number == 4
