"""Second candidate: independent patient-fit vetoes plus explicit completeness.

Used only in checkpointed development; never silently changes prior results.
"""
import json,re
from rag.verification_v6 import run_verification as preceding
from rag.patient_claim_policy_v7 import apply_policy
from services.groq_client import complete_json
from services.plan_sections import build_sections


def finalize(result,packet):
    result={**result,'patient_fit':{k:dict(v) for k,v in result['patient_fit'].items()}}
    fit=result['patient_fit'];p=packet['patient']
    if re.search(r'persistent.*(?:distress|ill)|deteriorat|critical|unwell',str(p.get('clinical_condition','')),re.I):
        fit['clinical_condition_reassuring']={'status':'not met','observed':p.get('clinical_condition'),'reason':'Recorded ongoing illness contradicts clinical reassurance'}
    suspicion=str(p.get('initial_suspicion','')).lower()
    fit['initial_suspicion_not_strong']={'status':'met' if suspicion in {'low','not strong'} else 'not met' if suspicion in {'strong','high'} else 'unknown','observed':p.get('initial_suspicion')}
    source_text=' '.join(e['text'] for e in packet['evidence'])
    hours=p.get('culture_incubation_hours');known_window=bool(re.search(r'36.{0,15}hour',source_text,re.I))
    fit['culture_incubation_window_met']={'status':'unknown' if hours is None or not known_window else 'met' if hours>=36 else 'not met','observed':hours,'reason':'The indexed 36-hour minimum is checked against culture incubation, never postnatal age; all other conditions remain independently required.'}
    if 'WHO' in packet.get('guideline','').upper():
        possible=p.get('referral_possible')
        fit['referral_not_possible']={'status':'not met' if possible is True else 'met' if possible is False else 'unknown','observed':possible}
        for field in ['feeding','movement','temperature_c','respiratory_rate','convulsions','severe_chest_indrawing']:
            value=p.get(field)
            fit[field+'_assessed']={'status':'unknown' if value is None or value in ['unknown','not documented'] else 'met','observed':value,'reason':'Assessment recorded is distinct from the presence or absence of an illness-category sign.'}
        fit['WHO_illness_category_established']={'status':'unknown','reason':'Do not collapse seven PSBI screening signs into clinical severe infection; missing signs require examination.'}
    accepted,findings=apply_policy(result,packet)
    result={**result,'accepted_claims':accepted,'independent_policy_findings':findings,
        'verification_version':'patient-fit-source-qualifiers-v7-development'}
    sections=build_sections(packet['patient'],'Recorded serial history: '+json.dumps(packet.get('history',[])),accepted,True)
    sections[1]['items'].append('Recorded context (source values and explicit unknowns): '+json.dumps(packet['patient'],ensure_ascii=False))
    p=packet['patient'];aliases={'feeding':['feeding','feeding_status','feeding_tolerance'],
        'movement':['movement','neurological_status'],'temperature':['temperature','neonatal_temperature'],'breathing':['respiratory_rate','respiratory_distress'],'oxygen saturation':['spo2']}
    missing=[k for k,keys in aliases.items() if not any(p.get(key) is not None and p.get(key) not in ['unknown','not documented','unavailable'] for key in keys)]
    result['uncertainty']={'criteria':result['patient_fit'],'missing_bedside_observations':missing,
        'clinical_review':'Required; unknown is not normal. Automated acceptance is not clinical adjudication.'}
    sections[0]['title']='Assessment scope and uncertainty'
    sections[0]['items'].append('Clinical judgement: '+json.dumps(result['uncertainty'],ensure_ascii=False))
    if missing:
        sections[5]['items'].insert(0,'Clinical judgement — do now: obtain the missing bedside examination and observations: '+', '.join(missing)+'. Do not infer reassurance or suitability for home observation from missing findings.')
    for section in sections:
        guideline=section['status']=='evidence_supported'
        if section['status']=='not_determined':section['items'].insert(0,'Not supported by retrieved evidence')
        section['items']=[('Guideline-derived '+ ' '.join('['+e+']' for e in section['evidence_labels'])+': ' if guideline else 'Recorded context / clinical judgement: ')+t for t in section['items']]
        if section['id'] in {'S06','S09','S10','S08'}:section['items']=[f'{i}. {t}' for i,t in enumerate(section['items'],1)]
    result['plan_sections']=sections
    result['caregiver_note']={'text':'The neonatal team is reviewing your baby’s observations and results. Ask the bedside team to explain the current concerns and next review. This research output does not establish that infection has been excluded.','origin':'clinical judgement; requires local clinician review'}
    covered={c['section'] for c in accepted};required=set(result['completeness']['required_sections'])
    result['completeness']={**result['completeness'],'supported_sections':sorted(covered),
        'passed':required<=covered and len(accepted)>=5,'all_13_sections_present':len(sections)==13}
    result['plan_release_status']='complete_for_research_review' if result['completeness']['passed'] else 'incomplete_for_research_review'
    return result


def run_verification(packet,settings,llm=complete_json):
    def constrained(prompt,settings,**kw):
        p=json.loads(prompt)
        p['additional_failure_regressions']=(
            'Do not reuse earlier normal SpO2 as a current normal measurement. '
            'Do not add concentration units to patient values if their recorded unit is absent. '
            'A diagnostic culture statement does not entail before-first-dose timing. '
            'Keep term-only exception wording term-only; a 35-week infant is not term. '
            'If a stopping condition is unknown, say explicitly do not recommend stopping for this patient; '
            'do not repeat a positive conditional stop instruction in the same claim. '
            'Do not invent observation frequencies, follow-up appointments or feeding-volume thresholds. '
            'Retain supported claims individually; unsupported sections are rendered explicitly, not filled by generic standard practice.')
        return llm(json.dumps(p,ensure_ascii=False,separators=(',',':')),settings,**kw)
    return finalize(preceding(packet,settings,constrained),packet)
