"""Build UI-compatible, source-grounded review responses without legacy scores."""
import json
from datetime import datetime, timezone
from domain.contraindication_rules import check_contraindications, flags_to_strings

from ml.features import NUMERIC, BOOLEAN, CATEGORIES
from rag.production_retrieval import retrieve, retrieve_plan
from rag.verification_graph import evidence_packet, run_verification
from services.plan_sections import build_sections
from schemas import (AntibioticPlanSchema, CitationItem, ClinicalCarePlanResponse,
                     EvidenceChunkResponse, EvidenceLabelRef, ExplanationResponse, FactCheckResult)

ALLOWED = set(NUMERIC) | set(BOOLEAN) | set(CATEGORIES) | {"penicillin_allergy", "blood_culture_positive", "age_hours"}
DISCLAIMER = "Research decision support. Clinician review is required; evidence checks do not establish clinical correctness or authorize treatment."


def sanitize_snapshot(snapshot):
    # No free text, names, MRNs, identifiers, dates or arbitrary object values.
    out = {}
    for k, v in snapshot.items():
        if k not in ALLOWED or v is None:
            continue
        if k in CATEGORIES:
            if v in CATEGORIES[k]:
                out[k] = v
        elif isinstance(v, (int, float, bool)):
            import math
            if math.isfinite(v):
                out[k] = v
    return out


def context_history(context, *, now=None):
    if not context:
        return []
    rows = []
    now=now or datetime.now(timezone.utc)
    for h in context.history[-30:]:
        # Relative timing is sufficient; dates are not sent to Groq.
        ts = h.get("created_at")
        try:
            if not isinstance(ts,str):raise ValueError('Missing history time')
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None or dt>now:raise ValueError('Unusable history time')
            hours_ago = round((now - dt).total_seconds() / 3600, 3)
        except (TypeError, ValueError):
            context.load_error='History contains missing, invalid or future assessment timestamps'
            return []
        rows.append({"hours_ago": hours_ago, "measurements": sanitize_snapshot(h.get("snapshot", {}))})
    return sorted(rows,key=lambda r:r['hours_ago'],reverse=True)


def summarize_trends(history,patient=None):
    history=list(history)
    if patient:history.append({'measurements':patient})
    parts = [f"{len(history)} recorded assessments available."]
    for key in ("heart_rate","respiratory_rate","spo2","crp_level", "neonatal_temperature", "creatinine_mg_dl", "platelet_count"):
        series = [r["measurements"][key] for r in history if r["measurements"].get(key) is not None]
        if len(series) >= 2:
            from services.plan_sections import MEASUREMENTS
            label,unit=MEASUREMENTS[key]
            parts.append(f"{label}: {series[0]} to {series[-1]} {unit} across {len(series)} measurements.")
    parts.append("These are observed changes, not an EOS diagnosis or a validated risk trend.")
    return " ".join(parts)


def produce(payload, guideline, settings, context=None):
    patient = sanitize_snapshot(payload.get("patient", {}))
    history = context_history(context)
    trend = summarize_trends(history,patient)
    query = f"early onset neonatal sepsis first 72 hours {guideline} evaluation monitoring escalation"
    # Expand with observed abnormality terms, never hand-built risk categories.
    for key in ("respiratory_distress", "oxygen_need", "neurological_status"):
        if patient.get(key) not in (None, "None", "Normal"):
            query += f" {key} {patient[key]}"
    if len(history) >= 2:
        query += " serial assessments CRP trend"
    if patient.get("creatinine_mg_dl") is not None:
        query += " renal function antibiotic safety"
    retrieval = retrieve_plan(guideline,settings,patient,context_query=query,history=history)
    packet = evidence_packet(retrieval.chunks, patient, history, guideline)
    packet['task_mode']='care_plan'
    age = patient.get("age_hours")
    if context and context.load_error:
        state = {'status':'abstained','errors':[context.load_error],'draft':{}}
    elif age is None or not 0 <= age < 72:
        state = {"status": "abstained", "errors": ["Age is missing or outside the 0-72-hour EOS scope"], "draft": {}}
    elif any(p!='ollama' for p in [settings.llm_provider,settings.verifier_provider or settings.llm_provider]) and not settings.allow_clinical_cloud_processing:
        state = {"status": "abstained", "errors": ["Cloud patient processing is not enabled for this deployment"], "draft": {}}
    else:
        state = run_verification(packet, settings)
    return format_plan(patient,history,retrieval,packet,state,settings,context=context)


def accepted_claims(state):
    """Release only claims explicitly checked and accepted by BOTH auditors.

    Any structural fault, incomplete audit or unassigned dissent blocks release.
    This does not change the frozen benchmark's whole-draft release protocol.
    """
    claims=state.get('draft',{}).get('claims',[])
    ids={c['id'] for c in claims}
    if not ids or state.get('citation_errors') or state.get('generation_error_code'):
        return []
    rejected=set()
    for key in ['evidence_verdict','safety_verdict']:
        review=state.get(key,{})
        checked=review.get('checked_claim_ids',[])
        failures=set(review.get('rejected_claim_ids',[]))
        if review.get('error_code') or set(checked)!=ids or len(checked)!=len(ids) or not failures<=ids:
            return []
        if review.get('supported') and (failures or review.get('reasons')):return []
        if not review.get('supported') and not failures:return []
        rejected.update(failures)
    return [c for c in claims if c['id'] not in rejected]


def format_plan(patient,history,retrieval,packet,state,settings,context=None):
    trend=summarize_trends(history,patient)
    released=accepted_claims(state)
    complete=state['status']=='supported_for_review' and not state.get('structural_rejections')
    supported=bool(released)
    if supported and not complete:state['status']='partially_supported_for_review'
    safety_flags = []
    if supported:
        proposed = [c["text"] for c in released]
        safety_flags = flags_to_strings(check_contraindications(patient, proposed, deltas=context.latest_deltas if context else None))
        if safety_flags:
            state["errors"].extend(safety_flags)
            state["status"] = "abstained"
            supported = False
    claims = released if supported else []
    labels = {e["id"]: e for e in packet["evidence"]}
    display_claims=list(claims)
    context_notes=[]
    # A red-flag fragment is not a stand-alone escalation pathway. Reuse the
    # complete framework only when that exact claim already passed both audits.
    # This changes presentation context, never the adjudicated claim population.
    if packet.get('task_mode')=='care_plan':
        frameworks=[c for c in claims if any(labels.get(s['evidence_id'],{}).get('chunk_id','').startswith('NICE-')
                    and 'use the following framework' in labels[s['evidence_id']]['text'].lower()
                    and c['text'].strip()==labels[s['evidence_id']]['text'].strip() for s in c['support'])]
        if frameworks:
            framework=max(frameworks,key=lambda c:len(c['text']))
            display_claims=[c for c in claims if c['section']!='escalation_criteria']+[{**framework,'section':'escalation_criteria'}]
            context_notes=['Display context: Escalation retains the complete assessment framework already accepted by both auditors, including its conditions.']
        else:
            def isolated_indicator(c):
                return c['section']=='escalation_criteria' and any(
                    'red flag' in labels.get(s['evidence_id'],{}).get('text','').lower()
                    and c['text'].strip()!=labels[s['evidence_id']]['text'].strip() for s in c['support'])
            display_claims=[c for c in claims if not isolated_indicator(c)]
            if len(display_claims)!=len(claims):context_notes=['Display context: an isolated red-flag fragment was withheld; no complete escalation framework passed both auditors.']
    def render(section):
        return [c["text"] + " " + " ".join(f"[{s['evidence_id']}]" for s in c["support"]) for c in display_claims if c["section"] == section]
    used = {s["evidence_id"] for c in claims for s in c["support"]}
    errors = state.get("errors", [])
    # No hand-authored medication plan is substituted when evidence fails.
    return ClinicalCarePlanResponse(
        plan_sections=build_sections(patient,trend,display_claims,supported),
        clinical_summary=(f"Infant assessed at {patient.get('age_hours','unknown')} hours; gestation {patient.get('gestational_age_weeks','unknown')} weeks. "
                          f"{len(claims)} source-supported discussion points are available for clinician review." if supported else "Automated care plan withheld: " + "; ".join(errors)),
        risk_analysis="\n".join(render("risk_analysis")) or "No validated numerical risk estimate is supplied by the language model.",
        trend_narrative=trend, driver_breakdown="Legacy point scores are excluded from this evidence synthesis.",
        recommended_actions=render("recommended_actions") if supported else ["Assess the infant directly and use the approved local neonatal pathway."],
        antibiotic_plan=AntibioticPlanSchema(required=False, urgency="Prescriber review; no automated treatment order", regimen=render('antibiotic_review'),
            duration="The prescriber must document the individual treatment duration.",
            stop_criteria="A stopping decision requires documented clinical review; no stopping order is generated.",
            decision_status="evidence_for_review" if render('antibiotic_review') else "undetermined"),
        monitoring_plan="\n".join(render("monitoring_plan")) or "Not determined by the automated system.",
        escalation_criteria="\n".join(render("escalation_criteria")) or "Seek neonatal clinical assessment; do not wait for an automated response if the infant is unwell.",
        parent_communication_notes="\n".join(render("parent_communication_notes")),
        citation_list=[CitationItem(source=e["source"], section=e["section"], chunk_id=e["chunk_id"], similarity_score=0, page_number=e["page_number"], file_name=e["file_name"], document_url=e["document_url"]) for label, e in labels.items() if label in used],
        evidence_labels=[EvidenceLabelRef(label=label, chunk_id=e["chunk_id"], source=e["source"], source_name=e["source"], section=e["section"], snippet=e["text"], page_number=e["page_number"], file_name=e["file_name"]) for label, e in labels.items() if label in used],
        rag_chunks=[EvidenceChunkResponse(**c.to_dict()) for c in retrieval.chunks],
        model_version=f"{settings.llm_provider}:{settings.local_llm_model if settings.llm_provider=='ollama' else settings.groq_model}/langgraph-v2", confidence_disclaimer=DISCLAIMER,
        fallback_used=not supported, contraindication_flags=safety_flags, fact_check=FactCheckResult(performed=bool(state.get("evidence_verdict")), verified=supported and complete, confidence=0,
            flagged_claims=errors, notes="Both source and safety auditors accepted every claim." if supported and complete else f"{len(claims)} claims accepted by both auditors; other claims were withheld. "+"; ".join(errors), judge_model=(settings.ollama_verifier_model or settings.local_llm_model) if (settings.verifier_provider or settings.llm_provider)=='ollama' else settings.verifier_model),
        verification_status=state["status"], verification_agents={k: state[k] for k in ("evidence_verdict", "safety_verdict") if k in state},
        retrieval_mode=retrieval.mode, retrieval_warnings=retrieval.warnings, corpus_version=retrieval.corpus_version,
        resolution_log=state.get('resolution_log',[])+context_notes+["No generated treatment order; clinician review required."],
        nutrition_fluid_plan='\n'.join(render('nutrition_fluids')),
    )


def explanation_from_plan(plan):
    return ExplanationResponse(clinical_summary=plan.clinical_summary, per_driver_explanations=[{'factor':'Observed course','explanation':plan.trend_narrative}],
        recommended_actions=plan.recommended_actions, evidence_summary=plan.risk_analysis,
        citation_list=plan.citation_list, confidence_disclaimer=plan.confidence_disclaimer, rag_chunks=plan.rag_chunks,
        model_version=plan.model_version, fallback_used=plan.fallback_used, fact_check=plan.fact_check, evidence_labels=plan.evidence_labels,
        verification_status=plan.verification_status,monitoring_plan=plan.monitoring_plan,
        escalation_criteria=plan.escalation_criteria,antibiotic_plan=plan.antibiotic_plan.model_dump(),
        trend_narrative=plan.trend_narrative)
