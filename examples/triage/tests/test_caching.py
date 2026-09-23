"""Nothing is re-read on its own: cached GitHub data and saved overviews stay
until someone asks for a refresh."""

import json

from triage import github, overview


def test_github_cache_does_not_expire_on_its_own(tmp_path):
    path = tmp_path / "issues.json"
    path.write_text(json.dumps({"fetched_at": 0, "data": [{"number": 1}]}))  # 1970
    assert github._cached(path, refresh=False) == [{"number": 1}]
    assert github._cached(path, refresh=True) is None


def test_an_overview_is_saved_and_read_back_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(overview, "SNAPSHOTS", tmp_path)
    assert overview.saved("o/r") is None
    overview._save("o/r", {"repo": {"slug": "o/r"}, "saved_at": 1.0})
    assert overview.saved("https://github.com/O/R")["repo"]["slug"] == "o/r"
