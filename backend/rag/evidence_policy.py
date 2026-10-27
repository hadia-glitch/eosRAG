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
    if meta.get('engineering_scope')=='late_only' or meta.get('population') in {'late_onset_neonatal','maternal_only','adult'}:
        return False
    # EOS scope is required even for a search without a loaded patient.
    # Otherwise a mixed source could bypass the scope gate via evidence search.
    if doc.get('mixed_population'):
        if (meta.get('population') not in {'early_onset_neonatal','neonatal_all_onset'}
            or not meta.get('scope_reviewed_by') or not meta.get('scope_reviewed_at')
            or not isinstance(meta.get('scope'),dict)):
            return False
    passage_scope=meta.get('scope')
    if passage_scope is not None:
        if not isinstance(passage_scope,dict):return False
        # Document-level limits cannot establish the scope of every passage
        # in a mixed guideline (for example WHO 0-6 versus 7-59 days).
        required={'gestational_age_weeks','postnatal_age_hours','care_setting'}
        if not required<=passage_scope.keys():return False
        for name in ['gestational_age_weeks','postnatal_age_hours']:
            bounds=passage_scope[name]
            if not isinstance(bounds,list) or len(bounds)!=2:return False
            import math
            if any(v is not None and (type(v) not in (int,float) or not math.isfinite(v)) for v in bounds):return False
            if all(v is not None for v in bounds) and bounds[0]>bounds[1]:return False
        settings_scope=passage_scope['care_setting']
        from rag.clinical_scope import setting_class,applicable
        if (not isinstance(settings_scope,list) or not settings_scope
            or any(not isinstance(v,str) or setting_class(v) is None for v in settings_scope)):return False
        age_lo=passage_scope['postnatal_age_hours'][0]
        if age_lo is not None and age_lo>=72:return False
        if patient is not None and not applicable(passage_scope,patient):return False
    if patient is not None:
        # Mixed documents can contain maternal, late-onset and early-onset
        # pathways. Document-level approval alone cannot admit every passage.
        # Source scope is reviewer-entered metadata, never inferred by an LLM.
        for field, prefix in (("gestational_age_weeks", "ga"), ("age_hours", "age_hours")):
            value = patient.get(field)
            lo, hi = doc.get("min_" + prefix), doc.get("max_" + prefix)
            import math
            if (any(type(v) not in (int,float) or not math.isfinite(v) for v in [value,lo,hi])
                or not lo <= value <= hi):
                return False
        from rag.clinical_scope import setting_class
        care=patient.get('care_setting')
        if care is not None:
            declared=doc.get('care_setting')
            declared=declared if isinstance(declared,list) else [declared]
            actual=setting_class(care)
            if not actual or any(not isinstance(v,str) for v in declared) or actual not in {setting_class(v) for v in declared}:
                return False
        elif doc.get('care_setting')!='hospital':
            # The existing hospital-only client predates the optional RAG
            # setting field. It cannot silently enter an outpatient pathway.
            return False
    return True


def verify_local_document(path, settings):
    doc = approved_document(path.name, settings)
    return doc if doc and hashlib.sha256(path.read_bytes()).hexdigest() == doc["sha256"] else None
