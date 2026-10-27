"""LangGraph: grounded draft -> isolated verifiers -> unanimous release.

An optional bounded resolution pass must receive fresh unanimous audits. Verifiers
receive the same source packet, patient measurements and draft claims, but no
generator rationale or each other's responses. Independence is procedural,
not a claim of statistically independent errors when models are shared.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from services.groq_client import GenerationUnavailable, complete_json
from rag.output_contracts import constrained_schema


class Support(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    quote: str = Field(min_length=12, max_length=1200)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^C[1-9][0-9]*$")
    section: Literal["risk_analysis", "recommended_actions", "monitoring_plan", "escalation_criteria", "parent_communication_notes", "investigations", "antibiotic_review", "nutrition_fluids", "follow_up"]
    text: str = Field(min_length=12, max_length=1500)
    support: list[Support] = Field(min_length=1, max_length=4)


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[Claim] = Field(min_length=1, max_length=16)


class QuoteReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quote_id: str = Field(pattern=r"^E[1-9][0-9]*Q[1-9][0-9]*$")


class IndexedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^C[1-9][0-9]*$")
    section: Literal["risk_analysis", "recommended_actions", "monitoring_plan", "escalation_criteria", "parent_communication_notes", "investigations", "antibiotic_review", "nutrition_fluids", "follow_up"]
    text: str = Field(min_length=12, max_length=1500)
    support: list[QuoteReference] = Field(min_length=1, max_length=4)


class IndexedDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[IndexedClaim] = Field(min_length=1, max_length=16)

class SourceSelectedClaim(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(pattern=r'^C[1-9][0-9]*$')
    section:Literal['risk_analysis','recommended_actions','investigations','antibiotic_review','monitoring_plan','escalation_criteria','nutrition_fluids','parent_communication_notes','follow_up']
    support:list[QuoteReference]=Field(min_length=1,max_length=1)

class SourceSelection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    claims:list[SourceSelectedClaim]=Field(min_length=1,max_length=16)


def index_quotes(packet,*,whole_recommendations=False):
    """Expose immutable source spans. Quote IDs are hints, never entailment proof."""
    import re
    quotes = {}
    evidence = []
    for source in packet['evidence']:
        text = ' '.join(source['text'].split())
        # Sentence/bullet boundaries retain wording. Long sentences use overlapping
        # contiguous spans; every span is still checked against its parent passage.
        parts = re.split(r'(?<=[.!?;])\s+|\s+[\u2022\u25cf\ufffd]\s+', text)
        # A complete short recommendation is one immutable quote, so its
        # conditions need not consume more than four fragmented quote IDs.
        spans = [text] if whole_recommendations and 12 <= len(text) <= 1200 else []
        for part in parts:
            if whole_recommendations and len(text)<=1200:break
            if len(part) < 12:
                continue
            for start in range(0, len(part), 600):
                span = part[max(0, start-100):start+600]
                if len(span) >= 12:
                    spans.append(span)
        if not spans and len(text) >= 12:
            spans = [text[:1200]]
        labeled = []
        for i, span in enumerate(spans, 1):
            key = f'{source["id"]}Q{i}'
            quotes[key] = {'evidence_id': source['id'], 'quote': span}
            labeled.append({'quote_id': key, 'text': span})
        evidence.append({**{k: v for k, v in source.items() if k != 'text'}, 'available_quotes': labeled})
    return {**packet, 'evidence': evidence}, quotes


def materialize_draft(response, quotes):
    # Full-quote responses remain supported for older clients/test adapters, but
    # must pass the same exact-source checks. No fuzzy matching or quote repair.
    if all('quote_id' not in s for c in response.get('claims', []) for s in c.get('support', [])):
        return Draft.model_validate(response)
    indexed = IndexedDraft.model_validate(response)
    claims = []
    for claim in indexed.claims:
        supports = []
        for support in claim.support:
            if support.quote_id not in quotes:
                raise ValueError('Unknown immutable quote ID')
            supports.append(quotes[support.quote_id])
        claims.append({**claim.model_dump(), 'support': supports})
    return Draft.model_validate({'claims': claims})


def selection_view(indexed_packet):
    """Retain all source wording, excluding repeated citation metadata."""
    return {**indexed_packet, 'evidence': [
        {k: e[k] for k in ('id', 'source', 'version', 'section', 'available_quotes') if k in e}
        for e in indexed_packet['evidence']]}


def materialize_selection(response, quotes):
    selection = SourceSelection.model_validate(response)
    claims = []
    for choice in selection.claims:
        key = choice.support[0].quote_id
        if key not in quotes:
            raise ValueError('Unknown selected source quote')
        claims.append({'id': choice.id, 'section': choice.section,
                       'text': quotes[key]['quote'], 'support': [quotes[key]]})
    return Draft.model_validate({'claims': claims})


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supported: StrictBool
    rejected_claim_ids: list[str] = Field(max_length=16)
    checked_claim_ids: list[str] = Field(min_length=1, max_length=16)
    reasons: list[str] = Field(max_length=16)


class State(TypedDict, total=False):
    packet: dict
    draft: dict
    citation_errors: list[str]
    evidence_verdict: dict
    safety_verdict: dict
    status: str
    errors: list[str]
    generation_error_code: str
    generation_validation_errors: list[dict]
    structural_rejections: list[dict]
    resolved_draft: dict


def evidence_packet(chunks, patient, history, guideline):
    return {"guideline": guideline, "patient": patient, "history": history,
            "evidence": [{"id": f"E{i}", "chunk_id": c.chunk_id, "source": c.source,
                          "version": c.version, "section": c.section, "text": c.chunk_text,
                          "page_number": c.page_number, "file_name": c.file_name, "document_url": c.document_url} for i, c in enumerate(chunks, 1)]}


def validate_support(draft: Draft, packet: dict) -> list[str]:
    sources = {e["id"]: e["text"] for e in packet["evidence"]}
    errors = []
    ids = [c.id for c in draft.claims]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate claim IDs")
    for claim in draft.claims:
        for support in claim.support:
            if support.evidence_id not in sources:
                errors.append(f"{claim.id}: unknown evidence label")
            elif " ".join(support.quote.split()) not in " ".join(sources[support.evidence_id].split()):
                errors.append(f"{claim.id}: quote is not verbatim source text")
        # Numeric doses are outside this generation contract. Dosing requires
        # a separate locally approved formulary with weight/age/renal checks.
        import re
        for match in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|microgram|ml|units?)(?:\b|/)",claim.text,re.I):
            # Recorded CRP/creatinine concentrations are observations, not doses.
            # This exception is narrow: exact recorded value, named analyte,
            # concentration unit and risk-discussion section must all match.
            before=claim.text[max(0,match.start()-65):match.start()]
            after=claim.text[match.end():match.end()+12]
            patient=packet.get('patient',{})
            lab=(('crp_level',r'(?:CRP|C.reactive protein)',r'^\s*/\s*(?:L|litre)\b'),
                 ('creatinine_mg_dl',r'creatinine',r'^\s*/\s*dL\b'))
            observation=claim.section=='risk_analysis' and match.group(2).lower()=='mg' and any(
                patient.get(key) is not None and float(match.group(1))==float(patient[key]) and
                re.search(name,before,re.I) and re.search(unit,after,re.I) for key,name,unit in lab)
            if not observation:
                errors.append(f"{claim.id}: numerical medication/fluid dosing is not supported")
                break
    return errors


def build_graph(settings, llm=complete_json):
    def generate(state):
        if state.get('resolved_draft'):
            draft=Draft.model_validate(state['resolved_draft'])
            return {'draft':draft.model_dump(),'citation_errors':validate_support(draft,state['packet'])}
        if not state["packet"]["evidence"]:
            return {"draft": {}, "citation_errors": ["No reviewed, applicable evidence was retrieved"]}
        indexed_packet, quotes = index_quotes(state['packet'],whole_recommendations=state['packet'].get('task_mode')=='care_plan')
        if state['packet'].get('task_mode')=='care_plan':
            # Source URLs, filenames, page offsets and database IDs stay in the
            # immutable server packet for citations. Repeating them in every
            # selection item wastes the provider's input budget; keep every
            # actual quote and its source/version/section in the model view.
            selection_packet=selection_view(indexed_packet)
            prompt=json.dumps({'task':'Select applicable guideline recommendations for a complete clinician-review plan. Return one claim for each supported section: risk_analysis (clinical indicators, not a numerical or high/low risk label), recommended_actions, investigations, antibiotic_review, monitoring_plan, escalation_criteria, nutrition_fluids (breastfeeding/expressing support when applicable), parent_communication_notes, follow_up (conditional planning, not permission to discharge). Each claim selects EXACTLY ONE existing quote_id. Choose a complete recommendation with all conditions, not a partial fragment that removes eligibility criteria. The application will display the actual source wording, separately from the observed patient findings. Do not invent quotes or add treatment orders. Prefer the immediate clinical-assessment recommendation for escalation. Use only recorded patient findings. If the infant is unwell or deteriorating, do not select reassurance or discharge eligibility without every required source condition; do not invent illness in a well infant. Select two investigations claims if needed to cover both blood culture and baseline CRP.',
                               'data':selection_packet,'coverage_note':'Select two antibiotic_review claims when supported: one for the empirical regimen option, and one for conditional treatment review/stopping. Select separate parent communication and nutrition support claims.'})
            try:
                draft=materialize_selection(llm(prompt,settings,role='You are the evidence synthesis agent.',
                    response_schema=constrained_schema(SourceSelection,quote_ids=quotes),completion_tokens=1200),quotes)
                return {'draft':draft.model_dump(),'citation_errors':validate_support(draft,state['packet'])}
            except GenerationUnavailable as exc:
                return {'draft':{},'citation_errors':['Source selection unavailable'],'generation_error_code':exc.code}
            except (ValueError,TypeError) as exc:
                return {'draft':{},'citation_errors':['Source selection failed validation'],
                        'generation_validation_errors':exc.errors(include_input=False,include_url=False)[:5] if hasattr(exc,'errors') else [{'type':type(exc).__name__}]}
        task = "Create up to six concise evidence-supported EOS discussion points for clinician review."
        if state['packet'].get('task_mode') == 'care_plan':
            task = ("Create a complete, concise clinician-review care plan, with 9-14 claims. Cover each of these sections "
                    "when supported: risk_analysis, recommended_actions, investigations, antibiotic_review, monitoring_plan, "
                    "escalation_criteria, nutrition_fluids, parent_communication_notes, follow_up. One concise claim per section "
                    "is enough. Do not omit supported investigations, antibiotic-review, parent-communication or handover guidance. "
                    "For antibiotic_review, describe guideline options conditionally, not a treatment order; do not give doses. "
                    "Retain ALL conditions in stopping, discharge, treatment-duration and monitoring recommendations. "
                    "Do not extrapolate observation-only pathways to a currently deteriorating infant. "
                    "Use at most four quote IDs per claim, preferably one complete recommendation quote. "
                    "Do not add monitoring frequencies, numerical thresholds, repeat-test rules or follow-up times absent in the selected quotes. "
                    "Patient facts must match the supplied values exactly; do not describe an unmet threshold as a present risk factor. "
                    "Prefer concise, faithful source extracts or very close paraphrases. Do not attach extra assertions to a sourced recommendation. "
                    "For risk_analysis, identify the relevant guideline clinical indicators without asserting an unvalidated risk level. "
                    "Do not turn severity or oxygen-support facts into assertions about the wording of a guideline list. "
                    "For escalation_criteria, state the source's immediate assessment advice; do not add seniority, transfer or timing requirements absent from that source. "
                    "Observed patient findings are rendered separately by the application: do not repeat biomarker numbers as diagnostic cutoffs. "
                    "For monitoring, use only the source's stated reassessment advice; do not invent continuous monitoring schedules. "
                    "For follow_up, keep post-discharge planning conditional; do not invent appointment intervals. "
                    "Keep breastfeeding support conditional on ability to feed, including support for expressing milk when temporarily unable. "
                    "If nutrition/fluid evidence is absent, omit that claim; never invent guidance to fill a heading.")
        prompt = json.dumps({"task": task + " Answer the evaluation_question if present. No risk scores or probabilities. Every claim must select existing quote_id values from available_quotes; never invent an ID or echo/paraphrase quotation text. Quotes are source support, not patient measurements. Include trends, monitoring, escalation, actions and risk discussion only if supported. Do not prescribe doses. No unsupported reassuring or antibiotic-stop statements.",
                             "output_schema": IndexedDraft.model_json_schema(), "data": indexed_packet})
        try:
            options={'response_schema':constrained_schema(IndexedDraft,quote_ids=quotes)} if settings.llm_schema_enforcement else {}
            draft = materialize_draft(llm(prompt, settings, role="You are the evidence synthesis agent.",**options), quotes)
            if state['packet'].get('task_mode')=='care_plan' and len({c.id for c in draft.claims})==len(draft.claims):
                safe=[];rejected=[]
                for claim in draft.claims:
                    failures=validate_support(Draft(claims=[claim]),state['packet'])
                    if failures:rejected.append({'id':claim.id,'reasons':failures})
                    else:safe.append(claim)
                if safe:
                    return {'draft':Draft(claims=safe).model_dump(),'citation_errors':[],
                            'structural_rejections':rejected}
            return {"draft": draft.model_dump(), "citation_errors": validate_support(draft, state["packet"])}
        except GenerationUnavailable as exc:
            return {"draft": {}, "citation_errors": ["Generation unavailable or schema invalid"], "generation_error_code": exc.code}
        except (ValueError, TypeError) as exc:
            details=exc.errors(include_url=False,include_input=False)[:5] if hasattr(exc,'errors') else [{'type':type(exc).__name__}]
            return {"draft": {}, "citation_errors": ["Generation unavailable or schema invalid"],
                    "generation_validation_errors":details}

    def verify(state, role):
        if not state.get("draft") or state.get("citation_errors"):
            return {"supported": False, "rejected_claim_ids": [], "checked_claim_ids": [], "reasons": ["Draft failed structural/source checks"]}
        packet=state['packet']
        audit_packet={k:packet.get(k) for k in ['guideline','patient','history']}
        audit_packet['evidence']=[{k:e.get(k) for k in ['id','source','section','version','text']} for e in packet['evidence']]
        # Exact quotations were already checked. Refer to their parent passages
        # without repeating those same paragraphs for every claim in the audit.
        audit_claims=[{**{k:c[k] for k in ['id','section','text']},
                      'support':[{'evidence_id':s['evidence_id']} for s in c['support']]} for c in state['draft']['claims']]
        prompt = json.dumps({"task": "Independently audit EVERY claim against its cited evidence passages AND recorded patient facts. Faithful paraphrases and combinations of multiple cited passages are allowed when every component is supported. Recorded patient facts are checked against patient/history, not required to occur in guideline text. Conditional guideline options are not claims that missing eligibility conditions have been met. Reject unsupported additions, contradiction, wrong population/gestation/setting, or essential missing information assumed normal. A citation alone is not entailment. Do not rewrite claims. checked_claim_ids must list every reviewed claim. If all pass, return supported=true and empty rejected_claim_ids and reasons. reasons lists failures only. Keep reasons concise.",
                             "source_packet": audit_packet, "claims": audit_claims})
        try:
            provider=settings.verifier_provider or settings.llm_provider
            model=(settings.ollama_verifier_model or settings.local_llm_model) if provider=='ollama' else settings.verifier_model
            options={'model':model,'completion_tokens':1000}
            if settings.llm_schema_enforcement:
                options['response_schema']=constrained_schema(Verdict,claim_ids={c['id'] for c in state['draft']['claims']})
            if provider!=settings.llm_provider:options['provider']=provider
            verdict = Verdict.model_validate(llm(prompt, settings, role=role, **options))
            expected = {c["id"] for c in state["draft"]["claims"]}
            if (set(verdict.checked_claim_ids) != expected or len(verdict.checked_claim_ids)!=len(expected)
                or not set(verdict.rejected_claim_ids)<=expected
                or (verdict.supported and (verdict.rejected_claim_ids or verdict.reasons))):
                raise ValueError("Incomplete or contradictory verdict")
            return verdict.model_dump()
        except GenerationUnavailable as exc:
            return {"supported": False, "rejected_claim_ids": [], "checked_claim_ids": [], "reasons": ["Verifier unavailable"], "error_code": exc.code}
        except (ValueError, TypeError):
            return {"supported": False, "rejected_claim_ids": [], "checked_claim_ids": [], "reasons": ["Verifier unavailable, incomplete, or invalid"]}

    def evidence(state):
        return {"evidence_verdict": verify(state, "You are an independent source-entailment auditor. Check citation scope, exact evidence support, negation, contradictions and source applicability.")}

    def safety(state):
        return {"safety_verdict": verify(state, "You are an independent neonatal safety auditor. Check patient age/gestation, trends, renal impairment, allergy, danger signs, missing data, and unsafe reassurance or discontinuation. Guidance is not an automatic treatment order.")}

    def release(state):
        errors = list(state.get("citation_errors", []))
        for key in ("evidence_verdict", "safety_verdict"):
            verdict = state[key]
            if not verdict.get("supported"):
                errors.extend(verdict.get("reasons") or [f"{key}: disagreement"])
        return {"status": "supported_for_review" if not errors else "abstained", "errors": errors}

    graph = StateGraph(State)
    graph.add_node("synthesize", generate)
    graph.add_node("evidence_auditor", evidence)
    graph.add_node("safety_auditor", safety)
    graph.add_node("release", release)
    graph.add_edge(START, "synthesize")
    graph.add_edge("synthesize", "evidence_auditor")
    graph.add_edge("synthesize", "safety_auditor")
    graph.add_edge(["evidence_auditor", "safety_auditor"], "release")
    graph.add_edge("release", END)
    return graph.compile()


def run_verification(packet, settings, llm=complete_json):
    # Persistent cross-patient LLM memory is deliberately absent: provenance
    # and reusable verification policies persist; patient prompts do not.
    started=time.monotonic()
    graph=build_graph(settings,llm)
    options={"recursion_limit":8,"max_concurrency":2}
    result=graph.invoke({'packet':packet},config=options)
    result['resolution_log']=[]
    expected={c['id'] for c in result.get('draft',{}).get('claims',[])}
    complete_reviews=bool(expected) and all(
        not result.get(key,{}).get('error_code') and
        set(result.get(key,{}).get('checked_claim_ids',[]))==expected
        for key in ['evidence_verdict','safety_verdict'])
    providers={settings.llm_provider,settings.verifier_provider or settings.llm_provider}
    timeout=max(settings.local_llm_timeout_seconds if p=='ollama' else settings.llm_timeout_seconds for p in providers)
    budget=getattr(settings,'verification_budget_seconds',80.)
    can_resolve=(getattr(settings,'verification_max_repairs',0)>0 and result['status']=='abstained'
                 and not result.get('citation_errors') and complete_reviews
                 and time.monotonic()-started+2*timeout<budget)
    if can_resolve:
        indexed,quotes=index_quotes(packet,whole_recommendations=packet.get('task_mode')=='care_plan')
        care_plan=packet.get('task_mode')=='care_plan'
        if care_plan:
            reverse={(q['evidence_id'],q['quote']):key for key,q in quotes.items()}
            previous_claims=[{'id':c['id'],'section':c['section'],
                'support_quote_ids':[reverse[(s['evidence_id'],s['quote'])] for s in c['support']]}
                for c in result['draft']['claims']]
            prompt=json.dumps({'task':'Revise this source selection ONCE using the unchanged source packet and reviewer findings. Preserve applicable accepted sections and replace rejected selections only when an applicable complete recommendation exists. Each claim selects EXACTLY ONE existing quote_id; its actual wording is materialized by the server. Cover all nine guidance sections only when supported. Retain all source conditions and explicit patient unknowns. Do not infer antibiotic exposure, negative cultures, eligibility for discharge or permission to stop treatment. Do not invent facts or doses. Do not claim reviewer approval; fresh audits decide release.',
                'data':selection_view(indexed),'previous_claims':previous_claims,
                'reviewer_findings':{k:result[k] for k in ['evidence_verdict','safety_verdict']}})
        else:
            prompt=json.dumps({'task':'Revise this discussion draft once using the unchanged source packet and the reviewer findings. Correct or remove unsupported inferences and wrong population claims. Preserve required conditions and explicit unknowns. Do not invent facts or doses. Select existing immutable quote IDs. Do not claim a reviewer approved the revision; fresh audits will decide release.',
                'output_schema':IndexedDraft.model_json_schema(),'data':indexed,
                'previous_claims':[{k:c[k] for k in ['id','section','text']} for c in result['draft']['claims']],
                'reviewer_findings':{k:result[k] for k in ['evidence_verdict','safety_verdict']}})
        previous={k:result.get(k) for k in ['draft','evidence_verdict','safety_verdict','status','errors']}
        try:
            schema_options={'response_schema':constrained_schema(SourceSelection if care_plan else IndexedDraft,quote_ids=quotes)} if care_plan or settings.llm_schema_enforcement else {}
            response=llm(prompt,settings,role='You are the source-grounded resolution agent.',completion_tokens=1200 if care_plan else 2200,**schema_options)
            revision=(materialize_selection if care_plan else materialize_draft)(response,quotes)
            errors=validate_support(revision,packet)
            if errors:raise ValueError('Revision failed exact-source or dose checks')
            result=graph.invoke({'packet':packet,'resolved_draft':revision.model_dump()},config=options)
            result['resolution_trace']=[previous]
            result['resolution_log']=['One source-grounded revision attempted after completed reviewer dissent.',
                'Both auditors independently rechecked every revised claim. Final status: '+result['status']+'.']
        except (GenerationUnavailable,ValueError,TypeError) as exc:
            result['resolution_trace']=[previous]
            result['resolution_log']=['Resolution did not complete valid source-grounded output; the original abstention is retained.']
            if isinstance(exc,GenerationUnavailable):result['resolution_error_code']=exc.code
    result["packet_sha256"] = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
    return result
