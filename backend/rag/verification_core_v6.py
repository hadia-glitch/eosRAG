"""Versioned development graph with bounded complete-audit retry.

The frozen graph remains untouched. Source approval and clinical deployment
remain separate gates. This copy preserves the original two audits and single
bounded resolution. No global monkeypatching is used.
"""
import hashlib,json,time
from langgraph.graph import END,START,StateGraph
from rag.verification_graph import (State,Draft,Verdict,SourceSelection,IndexedDraft,
    index_quotes,selection_view,materialize_selection,materialize_draft,evidence_packet)
from rag.output_contracts import constrained_schema
from rag.support_validation_v6 import validate_support
from rag.audit_contract_v6 import audit_with_retry
from services.groq_client import GenerationUnavailable,complete_json

FROZEN_CORE_SHA256 = '07b51352374f1dac88b236b9b5cf6199396b20218cb6131a7b4e3783dd17b07c'

def build_graph(settings, llm=complete_json):
    def generate(state):
        if state.get('resolved_draft'):
            draft=Draft.model_validate(state['resolved_draft'])
            return {'draft':draft.model_dump(),'citation_errors':validate_support(draft,state['packet'])}
        if not state["packet"]["evidence"]:
            return {"draft": {}, "citation_errors": ["No reviewed, applicable evidence was retrieved"]}
        indexed_packet, quotes = index_quotes(state['packet'],whole_recommendations=state['packet'].get('task_mode')=='care_plan')
        if False:  # v6 generates patient-conditioned claims, not quote-only selections.
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
        provider=settings.verifier_provider or settings.llm_provider
        model=(settings.ollama_verifier_model or settings.local_llm_model) if provider=='ollama' else settings.verifier_model
        options={'model':model,'completion_tokens':2400}
        if provider!=settings.llm_provider:options['provider']=provider
        return audit_with_retry(llm,prompt,settings,role,options,{c['id'] for c in state['draft']['claims']})

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
        care_plan=False
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
