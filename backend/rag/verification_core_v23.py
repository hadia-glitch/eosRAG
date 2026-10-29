"""Structured evidence application: source selection, immutable text, patient states.

There is no free-form model-authored treatment advice. This remains a research
candidate: source selection and human usefulness require independent review.
"""
import json,re,hashlib
from rag.source_selection_v11 import SourceSelection,validate_claims
from rag.patient_application_v23 import states
from rag.output_contracts import constrained_schema
from rag.audit_contract_v20 import audit_with_retry
from rag.verification_v6 import patient_fit
from rag.rendering_v23 import finalize
from services.groq_client import complete_json,GenerationUnavailable

SECTIONS=['risk_analysis','recommended_actions','investigations','antibiotic_review','monitoring_plan',
          'escalation_criteria','nutrition_fluids','parent_communication_notes','follow_up']


def run_verification(packet,settings,llm=complete_json):
    # Every quote choice is one COMPLETE indexed passage, never a condition-free
    # fragment. The model cannot supply a drug name, patient fact or prose claim.
    quotes={f"{e['id']}Q1":{'evidence_id':e['id'],'quote':e['text']} for e in packet['evidence']}
    preview=finalize({'draft':{},'patient_fit':patient_fit(packet),'accepted_claims':[], 'completeness':{'required_sections':[]}},packet)
    application={**preview['patient_fit'],**states(packet)}
    intents={
      'risk_analysis':'Compare recorded or missing findings with the cited clinical indicators, biomarker limitations or stopping criteria. This is not a numerical risk category and does not assert that a listed sign is present.',
      'recommended_actions':'Provide relevant conditional clinical-assessment or referral guidance for discussion, not an invented patient treatment order.',
      'investigations':'Explain available diagnostic guidance and its conditions, including source-supported bedside assessment or clinical sign algorithms when laboratory testing is not addressed. A bedside-assessment reference must not be represented as laboratory guidance. A diagnostic reference does not mean a new sample or lumbar puncture is ordered.',
      'antibiotic_review':'Show the treatment, review, duration or stopping options actually addressed by each cited source, alongside patient criterion states. A regimen-only reference does not assert a stopping rule; label absent stopping guidance explicitly rather than rejecting relevant regimen context for not containing a full stopping protocol. Unmet or unknown criteria explicitly mean the system does not recommend stopping.',
      'monitoring_plan':'Show the source-supported clinical observation or review options actually mentioned. Do not require this reference to define an entire monitoring protocol or invent a frequency.',
      'escalation_criteria':'Identify source-described clinical-assessment/referral triggers for comparison with current or missing findings, not an invented treatment escalation.',
      'nutrition_fluids':'Show the feeding or breastfeeding support actually addressed by the source; no fluid prescription or claim that all nutrition/fluid management is covered.',
      'parent_communication_notes':'Show the counselling topics actually supported, without claiming a discharge decision or reassurance.',
      'follow_up':'Show only applicable follow-up/handover guidance for the current pathway; a background study, maternal future-pregnancy advice or unrelated long-term disease follow-up does not qualify.'}
    prompt={'task':'Select complete passages for the nine care-plan topics in sections. Use zero to four existing quote IDs per claim; an empty list explicitly means no supporting source for that topic. Return one row for each of the nine topics, with zero to four existing quote IDs each. Use an empty list for an unsupported topic. Do not omit available observation/reassessment sources for monitoring and escalation; preserve what the source actually addresses. Return only existing quote IDs. No authored treatment prose. Select only useful evidence for this infant and its actual setting. Missing observations require assessment before reassurance. When referral_possible=true, the outpatient alternative is not eligible. A combined source containing a valid primary hospital-referral recommendation may be selected as a criteria reference only; its unavailable alternative branch will be explicitly marked not met. Do not select background studies as clinical instructions. Include complete exception context when selecting a stopping rule. A stopping rule is displayed as a criteria reference, never permission to stop. Omit a topic when its evidence is absent.',
        'sections':SECTIONS,'section_intents':intents,'patient_application':application,'patient':packet['patient'],'history':packet.get('history',[]),
        'evidence':[{'quote_id':e['id']+'Q1','source':e.get('source'),'text':e['text']} for e in packet['evidence']]}
    generation_error=None;contract_rejections=[];unsupported_sections=[]
    try:
        raw=llm(json.dumps(prompt,ensure_ascii=False,separators=(',',':')),settings,
            role='You are the evidence synthesis agent.',response_schema=constrained_schema(SourceSelection,quote_ids=quotes),completion_tokens=1400)
        selections,contract_rejections,unsupported_sections=validate_claims(raw,quotes)
    except GenerationUnavailable as exc:
        generation_error=exc.code;selections=[]
    except (ValueError,TypeError):
        generation_error='model_json_contract_failure';selections=[]
    evidence={e['id']:e for e in packet['evidence']};claims=[];selection_rejections=list(contract_rejections)
    for c in selections:
        supports=[];parents=[]
        for ref in c.support:
            if ref.quote_id not in quotes:raise ValueError('Unknown quote ID')
            support=quotes[ref.quote_id]
            if support['evidence_id'] not in {x['evidence_id'] for x in supports}:
                supports.append(support);parents.append(evidence[support['evidence_id']])
        text='\n\n'.join(s['quote'] for s in supports)
        reason=None
        topic_checks={'follow_up':r'follow.up|discharg|after stopping', 'parent_communication_notes':r'parent|carer|caregiver|counsel|discuss|explain', 'nutrition_fluids':r'breastfeed|breast milk|express.*milk|nutrition|fluid'}
        if c.section in topic_checks and not re.search(topic_checks[c.section],text,re.I):reason='Selected passage does not cover the named section'
        if re.search(r'\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|µg|μg|micrograms?|units?)\s*/\s*kg\b',text,re.I):reason='Drug-dose passage is outside this display contract'
        therapeutic=re.search(r'\b(?:ampicillin|amoxicillin|gentamicin|penicillin|benzylpenicillin|dose|dosage|administer|inject|infuse|bolus)\b',text,re.I)
        if therapeutic and re.search(r'\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|µg|μg|micrograms?|units?)\b(?!\s*/\s*(?:L|dL|mL)\b)',text,re.I):reason='Numerical therapeutic dose is outside this display contract'
        exposure=packet['patient'].get('antibiotic_exposure_hours',packet['patient'].get('antibiotic_duration_hours'))
        if c.section=='investigations' and exposure is not None and exposure>0 and re.search(r'before\s+(?:giving\s+)?(?:the\s+)?first\s+(?:antibiotic\s+)?dose|before\s+(?:initiating|starting).*antibiotic',text,re.I):
            pass  # Historical labelling must never clear an existing rejection.
        referral_path=bool(re.search(r'referral.{0,35}(?:not possible|not feasible)',text,re.I))
        if packet['patient'].get('referral_possible') is True and referral_path and c.section in {'antibiotic_review','monitoring_plan','follow_up','recommended_actions'}:
            pass  # Conditional labelling must never clear an existing rejection.
        if all(parent.get('kind')=='supplemental_publisher_definition' for parent in parents) and c.section!='risk_analysis':reason='Definition is not an action recommendation'
        if reason:selection_rejections.append({'id':c.id,'reason':reason,'evidence_ids':[s['evidence_id'] for s in supports]});continue
        claims.append({'id':c.id,'section':c.section,'text':text,'support':supports})
    state={'draft':{'claims':claims},'citation_errors':[], 'structural_rejections':selection_rejections}
    # Auditors judge relevance/scope; they cannot approve fabricated words,
    # because the rendered recommendation is the exact parent passage.
    for key,role in [('evidence_verdict','You are an independent source-entailment auditor.'),('safety_verdict','You are an independent neonatal safety auditor.')]:
        if not claims:
            state[key]={'supported':False,'checked_claim_ids':[],'rejected_claim_ids':[],'reasons':['No eligible source selections']};continue
        audit={'task':'Audit relevance, population, age, care setting, whole-passage scope and usefulness of each source reference for this patient. These are COMPLETE immutable source references, not orders or assertions the patient has a listed sign. Patient facts and eligibility will be rendered separately with unknowns explicit. Reject wrong pathways, background used as an action, missing required exception context, or sections unsupported by their source. Do not infer normal observations.',
            'patient':packet['patient'],'history':packet.get('history',[]),'patient_application':application, 'interpretation_contract':'A rule with unmet/unknown criteria is retained to explain non-eligibility, not to assert it is met. A source reference is relevant to explaining why stopping is not established. It must never be turned into a recommendation to stop. Distinguish this purpose from a proposed patient action. Judge the narrow claim_statement actually supplied, not an imagined comprehensive management statement. An unmet rule can be relevant evidence explaining non-eligibility; it does not assert eligibility. Do not reject a breastfeeding-support reference merely because it is not a complete fluid prescription. Do not reject a reference solely for containing an alternative branch explicitly marked not met: evaluate the claim intent and patient-application labels. Still reject unrelated evidence, invented eligibility, or actual recommendations of wrong pathways. Require actual topic coverage; background outcome studies are not follow-up instructions.', 'claims':[{'id':c['id'],'section':c['section'],'purpose':'criteria comparison; no automatic patient action','claim_statement':intents[c['section']],'evidence_ids':[s['evidence_id'] for s in c['support']]} for c in claims], 'evidence':[e for e in packet['evidence'] if e['id'] in {s['evidence_id'] for c in claims for s in c['support']}]}
        state[key]=audit_with_retry(llm,json.dumps(audit,ensure_ascii=False),settings,role,
            {'model':settings.verifier_model if key=='evidence_verdict' else 'qwen/qwen3.8-27b','completion_tokens':1700 if key=='evidence_verdict' else 900},{c['id'] for c in claims})
    expected={c['id'] for c in claims};bad=set();complete=bool(expected)
    for key in ['evidence_verdict','safety_verdict']:
        v=state[key]
        complete=complete and not v.get('error_code') and set(v.get('checked_claim_ids',[]))==expected
        bad.update(v.get('rejected_claim_ids',[]))
    accepted=[c for c in claims if c['id'] not in bad] if complete else []
    # Reuse the versioned record/unknown renderer, but do not treat quoted stop
    # rules as imperative patient instructions. Source references stay distinct.
    initial={**state,'patient_fit':patient_fit(packet),'accepted_claims':[],
        'completeness':{'required_sections':['recommended_actions','investigations','antibiotic_review','monitoring_plan','escalation_criteria']}}
    result=finalize(initial,packet)
    if generation_error:result['generation_error_code']=generation_error
    result['source_reference_claims']=accepted
    result['status']='source_references_reviewed' if complete else 'abstained'
    result['verification_version']='offline-fixes-v23-pending-fresh-evaluation'
    result['patient_application']=application
    result['unsupported_selection_sections']=unsupported_sections
    result['selection_rejections']=selection_rejections
    mapping=dict(zip(SECTIONS,[4,5,6,7,8,9,10,11,12]))
    exposure=packet['patient'].get('antibiotic_exposure_hours',packet['patient'].get('antibiotic_duration_hours'))
    for c in accepted:
        section=result['plan_sections'][mapping[c['section']]]
        if section['status']!='evidence_supported':section['items']=[]
        section['status']='evidence_supported';section['evidence_labels']=sorted(set(section['evidence_labels']+[s['evidence_id'] for s in c['support']]))
        section['items'].append('Guideline-derived criteria/reference ['+', '.join(s['evidence_id'] for s in c['support'])+'] (not an automatic treatment order): '+c['text'])
        section['patient_application']=application
        section['items'].insert(0,'Recorded context / clinical judgement — applicability: '+('This pre-first-dose reference is historical; treatment has already started, so it is not a new sampling instruction. ' if exposure is not None and exposure>0 and 'first dose' in c['text'].lower() else '')+('The referral-unavailable branch is NOT MET for this patient because referral is recorded possible. It is not an outpatient treatment instruction. ' if packet['patient'].get('referral_possible') is True and re.search(r'referral.{0,35}(?:not possible|not feasible)',c['text'],re.I) else '')+'Review the explicit met / not met / unknown states; this reference does not authorize a patient order.')
    stop=result['plan_sections'][7]
    stop['items'].insert(0,'Clinical judgement — patient application: no recommendation to stop antibiotics is made by this system. Review the met / not met / unknown criteria and the actual clinical condition with the responsible prescriber. Unknown incubation, missing examination or persistent illness is not reassurance.')
    missing=result['uncertainty']['missing_bedside_observations']
    result['plan_sections'][5]['items'].insert(0,'1. Clinical judgement — do now: '+('obtain missing bedside observations: '+', '.join(missing) if missing else 'review the recorded clinical condition and ongoing concerns with the neonatal clinician')+'.')
    covered={c['section'] for c in accepted};required=set(initial['completeness']['required_sections'])
    result['completeness']={'all_13_sections_present':True,'required_sections':sorted(required),'supported_sections':sorted(covered),'passed':required<=covered and len(accepted)>=5}
    result['plan_release_status']='structured_evidence_review_only' if result['completeness']['passed'] else 'incomplete_for_research_review'
    result['clinical_ready']=False;result['clinical_usability_established']=False
    for section in result['plan_sections']:
        if section['id'] in {'S06','S08','S09','S10'}:
            section['items']=[f'{i}. {item}' for i,item in enumerate(section['items'],1)]
    result['packet_sha256']=hashlib.sha256(json.dumps(packet,sort_keys=True).encode()).hexdigest()
    return result
