import hashlib
from copy import deepcopy
import pytest
from rag.clinical_evidence_brief import build_evidence_brief


def fixture():
    text = "Stop only if cultures are sterile, unless there is site-specific infection."
    source = {"raw_text": text, "text_sha256": hashlib.sha256(text.encode()).hexdigest()}
    packet = {"patient": {"age_hours": 24, "culture_status": "unknown", "temperature_c": None},
              "history": [{"age_hours": 12, "respiratory_rate": 55}],
              "evidence": [{"chunk_id": "S1", "text": text}]}
    return packet, {"S1": source}


def test_complete_exception_unknowns_and_input_independence():
    packet, sources = fixture(); original = deepcopy(packet)
    result = build_evidence_brief(packet, sources)
    assert result["complete_source_passages"][0]["text"] == sources["S1"]["raw_text"]
    assert result["explicit_unknown_fields"] == ["culture_status", "temperature_c"]
    assert result["clinical_eligibility_established"] is False
    result["recorded_current"]["culture_status"] = "negative"
    assert packet == original


@pytest.mark.parametrize("bad", ["fabricated", "truncated"])
def test_refuses_modified_or_unindexed_sources(bad):
    packet, sources = fixture()
    if bad == "fabricated": packet["evidence"][0]["chunk_id"] = "S2"
    else: packet["evidence"][0]["text"] = "Stop only if cultures are sterile."
    with pytest.raises(ValueError): build_evidence_brief(packet, sources)


@pytest.mark.parametrize("time", [24, 25, float("nan"), True])
def test_refuses_unavailable_history(time):
    packet, sources = fixture(); packet["history"][0]["age_hours"] = time
    with pytest.raises(ValueError): build_evidence_brief(packet, sources)
