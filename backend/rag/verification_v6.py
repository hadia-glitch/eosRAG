"""Patient-conditioned full-plan development candidate; never clinical approval."""
import json,re
from rag.verification_core_v6 import run_verification as core
from rag.audit_contract_v6 import approved_claims
from services.groq_client import complete_json
from services.plan_sections import build_sections

CONTRACT='''Generate 9-14 atomic claims for a numbered patient-specific care plan: do now, monitor, escalate/de-escalate. Cover risk_analysis, recommended_actions, investigations, antibiotic_review, monitoring_plan, escalation_criteria, nutrition_fluids, parent_communication_notes and follow_up only when supported. The renderer supplies all 13 headings and explicit unsupported placeholders. Every guideline statement requires immutable quote IDs. Label clinical judgement explicitly; it must not masquerade as sourced evidence. Give no drug doses. State met/not met/unknown for stopping and treatment conditions using actual observations, trends, culture status AND culture incubation time; postnatal age is not incubation time. Never recommend stopping when reassurance is unknown or contradicted. Missing examination, feeding, movement, temperature or breathing requires obtaining those observations before reassurance or home care. Preserve every exception, including AAP unexplained critical cardiorespiratory illness and site-specific infection, with correct gestational scope. Do not call NICE other clinical indicators red flags or invent moderate-risk labels. AAP categorical group 4 is inadequate prophylaxis, not adequate; use the exact retrieved definition. WHO PSBI, clinical severe infection, isolated fast breathing and critical illness are different definitions. Drug names must match the exact source AND hospital/referral pathway; never substitute amoxicillin for hospital ampicillin. Blood culture before first dose, baseline CRP and review while continuing antibiotics belong only to passages actually retrieved and applicable. Do not invent a retrospective pre-dose sampling opportunity, routine tests, CSF at a fixed elapsed time, placental pathology, or observation intervals. Unsupported sections remain unsupported. Include uncertainty and a short sourced caregiver communication note. Quoted conditions do not establish this infant meets them.'''


def patient_fit(packet):
    p=packet['patient'];culture=p.get('culture_status','unknown')
    reassuring=p.get('clinical_condition_reassuring')
    illness=p.get('clinical_condition',p.get('clinical_status',''))
    if p.get('persistent_illness') is True or re.search(r'unwell|critical|persistent.*ill|deteriorat',str(illness),re.I):reassuring=False
    return {
        'negative_culture':{'status':'met' if culture=='negative' else 'not met' if culture=='positive' else 'unknown','observed':culture},
        'culture_incubation_recorded':{'status':'met' if p.get('culture_incubation_hours') is not None else 'unknown','observed':p.get('culture_incubation_hours')},
        'clinical_condition_reassuring':{'status':'met' if reassuring is True else 'not met' if reassuring is False else 'unknown','observed':reassuring},
        'CRP_trend_reassuring':{'status':'unknown','observed':{'current':p.get('crp',p.get('crp_level')),'history':packet.get('history',[])},'reason':'A falling CRP alone does not establish clinical reassurance; no universal cutoff is invented.'},
        'RR_and_SpO2':{'status':'unknown','observed':{k:p.get(k) for k in ['respiratory_rate','spo2']},'reason':'Recorded values are retained; clinical examination and guideline-specific interpretation are required.'},
        'site_specific_infection_excluded':{'status':'met' if p.get('site_specific_infection') is False else 'not met' if p.get('site_specific_infection') is True else 'unknown','observed':p.get('site_specific_infection')},
        'unexplained_critical_cardiorespiratory_illness_absent':{'status':'met' if p.get('unexplained_critical_cardiorespiratory_illness') is False else 'not met' if p.get('unexplained_critical_cardiorespiratory_illness') is True else 'unknown','observed':p.get('unexplained_critical_cardiorespiratory_illness')}}


def run_verification(packet,settings,llm=complete_json):
    packet={**packet,'task_mode':'care_plan'};fit=patient_fit(packet)
    def bounded(prompt,settings,**kw):
        p=json.loads(prompt)
        p['patient_fit_review']=fit
        if 'auditor' in kw.get('role',''):
            p['patient_fit_and_completeness_checks']=CONTRACT+' Reject or flag each omitted exception, incorrect category, wrong regimen/pathway, unjustified reassurance or patient-condition contradiction. A verbatim quotation can still be irrelevant or unsafe for this case.'
        else:p['task']=CONTRACT
        return llm(json.dumps(p,ensure_ascii=False,separators=(',',':')),settings,**kw)
    result=core(packet,settings.model_copy(update={'llm_schema_enforcement':True}),bounded)
    accepted=approved_claims(result);rejected=[]
    for c in accepted:
        text=c['text']
        if re.search(r'\b(?:stop|discontinu\w*)\b.{0,50}\bantibiotic',text,re.I) and any(v['status']!='met' for k,v in fit.items() if k in {'negative_culture','culture_incubation_recorded','clinical_condition_reassuring','site_specific_infection_excluded','unexplained_critical_cardiorespiratory_illness_absent'}):
            # An unrelated negation ("CRP cannot exclude") must not excuse a
            # positive stop instruction elsewhere in the same claim.
            negative=re.search(r'\b(?:cannot|must not|do not|should not)\s+(?:recommend\s+)?(?:stop|discontinu\w*)\b|\b(?:stopping|discontinuation)\b.{0,35}\b(?:not established|not appropriate|not supported|unknown|not met)\b',text,re.I)
            positive=re.search(r'\b(?:should|may|can|recommend|consider)\s+(?:be\s+)?(?:discontinu\w*|stopp?\w*)\b|\b(?:discontinue|stop)\s+(?:the\s+)?(?:empiri\w*\s+)?antibiotics?\s+(?:at|after|by|when)\b',text,re.I)
            if not negative or positive:rejected.append(c['id'])
    accepted=[c for c in accepted if c['id'] not in rejected]
    sections=build_sections(packet['patient'],'Recorded longitudinal observations: '+json.dumps(packet.get('history',[])),accepted,True)
    for s in sections:
        if s['status']!='evidence_supported' and s['status']!='recorded':s['items'].insert(0,'Not supported by retrieved evidence')
        s['items']=[('Guideline-derived '+ ' '.join('['+e+']' for e in s['evidence_labels'])+': ' if s['status']=='evidence_supported' else 'Clinical judgement / recorded context: ')+t for t in s['items']]
    sections[0]['items'].append('Uncertainty: '+json.dumps(fit,ensure_ascii=False))
    for s in sections:
        if s['id']=='S06':s['items']=[f'{i}. {t}' for i,t in enumerate(s['items'],1)]
    covered={c['section'] for c in accepted};required={'recommended_actions','investigations','antibiotic_review','monitoring_plan','escalation_criteria'}
    result.update(verification_version='patient-fit-claim-level-v6-development',accepted_claims=accepted,
        patient_fit=fit,patient_fit_rejected_claim_ids=rejected,plan_sections=sections,
        completeness={'required_sections':sorted(required),'supported_sections':sorted(covered),'passed':required<=covered and len(accepted)>=5},
        clinical_ready=False,clinical_usability_established=False)
    result['plan_release_status']='complete_for_research_review' if result['completeness']['passed'] else 'incomplete_for_research_review'
    return result
