"""Lossless research evidence view; never infers treatment eligibility.

This deliberately does not release free-form model reasoning. Its integrity
checks establish source fidelity, not clinical relevance or safety approval.
"""
from copy import deepcopy
import hashlib
import math


UNKNOWN = {"unknown", "unavailable", "not fully documented", "unclear", "not documented"}


def build_evidence_brief(packet, indexed_sources):
    """Separate recorded values from complete, hash-verified indexed passages.

    Caller supplies the trusted corpus, never a corpus returned by a model.
    No claim, quote selection, dose recommendation or eligibility assertion
    from a model is used. Reject stale/future history rather than silently
    displaying an impossible longitudinal sequence.
    """
    patient = deepcopy(packet["patient"])
    history = deepcopy(packet.get("history", []))
    age = patient.get("age_hours")
    if isinstance(age, bool) or not isinstance(age, (float, int)) or not math.isfinite(age) or not 0 <= age <= 72:
        raise ValueError("An explicit EOS assessment age in hours is required")
    previous = -1
    for row in history:
        t = row.get("age_hours")
        if isinstance(t, bool) or not isinstance(t, (float, int)) or not math.isfinite(t) or not previous < t < age:
            raise ValueError("History must be strictly chronological and before assessment")
        previous = t
    passages = []
    seen = set()
    for ref in packet.get("evidence", []):
        cid = ref["chunk_id"]
        if cid in seen or cid not in indexed_sources:
            raise ValueError("Duplicate or unindexed evidence")
        source = indexed_sources[cid]
        text = source["raw_text"]
        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest != source["text_sha256"] or ref["text"] != text:
            raise ValueError("Source text/hash mismatch")
        seen.add(cid)
        passages.append({"chunk_id": cid, "text": text, "text_sha256": digest,
                         "source": source.get("source"), "section": source.get("section"),
                         "version": source.get("version"), "pdf_page": source.get("pdf_page"),
                         "kind": ref.get("kind", "recommendation")})
    if not passages:
        raise ValueError("No indexed evidence available")
    unknowns = [key for key, value in patient.items()
                if value is None or isinstance(value, str) and value.lower().strip() in UNKNOWN]
    return {
        "version": "lossless-evidence-brief-v1-research",
        "status": "source_comparison_only",
        "question": packet.get("evaluation_question", ""),
        "recorded_current": patient, "recorded_history": history,
        "explicit_unknown_fields": unknowns,
        "complete_source_passages": passages,
        "clinical_eligibility_established": False,
        "clinical_validation": False,
        "interpretation_boundary": (
            "Recorded findings and complete source passages are displayed separately. "
            "Unknown does not mean normal, absent, reassuring, or a satisfied condition. "
            "No stopping, discharge, treatment, diagnosis or illness-category eligibility "
            "is established by this view. All source conditions and exceptions require "
            "clinical review; retrieval alone does not establish applicability."
        ),
    }
