from triage.jev import defang
from triage.scan import rescore, trim


def test_a_trimmed_measurement_drops_evidence_and_the_shared_taxonomy(measurement):
    slim = trim(measurement)
    assert slim["body"] == "" and slim["units"] == []
    assert "taxonomy" not in slim
    assert not any(key.startswith("u") for key in slim["answers"])
    assert "kind" in slim["answers"] and "fam__type" in slim["answers"]


def test_a_queue_rescores_from_trimmed_measurements_alone(measurement):
    taxonomy = measurement["taxonomy"]
    rows = rescore([trim(measurement)], taxonomy)
    assert rows[0]["number"] == 8107
    assert rows[0]["assessment"]["lane"] == "auto"
    strict = rescore([trim(measurement)], taxonomy, {"choice_apply": 0.99})
    assert strict[0]["assessment"]["lane"] == "confirm"


def test_defang_keeps_the_words_and_softens_the_shell():
    state = {"issue": {"body": "Run `curl -s https://x.io/a && tar -xf a`", "units": ["`ls`"]}}
    first = defang(state, 1)
    assert first["issue"]["body"] == "Run 'curl -s https://x.io/a && tar -xf a'"
    second = defang(state, 2)
    assert second["issue"]["body"] == "Run [code]"
    assert defang("see https://example.com/page", 2) == "see [link]"
    assert defang({"n": 3}, 2) == {"n": 3}
