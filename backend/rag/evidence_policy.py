"""Explicit corpus admission. A filename or model confidence is not provenance."""
import hashlib
import json
from pathlib import Path


def load_manifest(settings):
    try:
        raw = Path(settings.evidence_manifest_path).read_bytes()
        data = json.loads(raw)
        return data["documents"], hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, KeyError):
        return [], "unavailable"


def approved_document(filename, settings):
    documents, _ = load_manifest(settings)
    return next((d for d in documents if d.get("file_name") == filename and d.get("approved_for_generation") is True
                 and d.get("reviewed_by") and d.get("reviewed_at") and d.get("status") == "current"
                 and d.get("sha256") and str(d.get("url", "")).startswith("https://")), None)


def admit_chunk(chunk, settings, guideline=None, patient=None):
    meta = chunk.get("metadata") or {}
    doc = approved_document(meta.get("file_name", chunk.get("file_name", "")), settings)
    if not doc:
        return False
    if meta.get("document_sha256") != doc["sha256"] or chunk.get("version") != doc["version"]:
        return False
    if guideline and doc["source"].upper() != guideline.upper():
        return False
    if patient is not None:
        # Mixed documents can contain maternal, late-onset and early-onset
        # pathways. Document-level approval alone cannot admit every passage.
        if doc.get('mixed_population'):
            if (meta.get('population') not in {'early_onset_neonatal','neonatal_all_onset'}
                or not meta.get('scope_reviewed_by') or not meta.get('scope_reviewed_at')):
                return False
        # Source scope is reviewer-entered metadata, never inferred by an LLM.
        for field, prefix in (("gestational_age_weeks", "ga"), ("age_hours", "age_hours")):
            value = patient.get(field)
            lo, hi = doc.get("min_" + prefix), doc.get("max_" + prefix)
            if value is None or lo is None or hi is None or not lo <= value <= hi:
                return False
        if doc.get("care_setting") != "hospital":
            return False
    return True


def verify_local_document(path, settings):
    doc = approved_document(path.name, settings)
    return doc if doc and hashlib.sha256(path.read_bytes()).hexdigest() == doc["sha256"] else None
