"""Independent, conservative checks for observed development failure patterns.

These are release vetoes, not sepsis diagnostic thresholds or clinical approval.
The unchanged drafts and both model verdicts remain available for adjudication.
"""
import re


def violations(claim,packet,fit):
    text=claim['text'];t=' '.join(text.lower().split());quotes=' '.join(s['quote'] for s in claim['support']).lower()
    errors=[];source=packet.get('guideline','').upper();patient=packet['patient']
    stopping=bool(re.search(r'\b(?:stop|stopping|stopped|discontinu\w*)\b',t)) and 'antibiotic' in t
    if stopping:
        required=['negative_culture','culture_incubation_window_met','clinical_condition_reassuring','site_specific_infection_excluded']
        if 'AAP' in source:required.append('unexplained_critical_cardiorespiratory_illness_absent')
        if 'NICE' in source:required+=['CRP_trend_reassuring','initial_suspicion_not_strong']
        unavailable=any(fit.get(k,{'status':'unknown'})['status']!='met' for k in required)
        negative=re.search(r'\b(?:cannot|must not|do not|should not)\s+(?:recommend\s+)?(?:stop|discontinu\w*)\b|\b(?:stopping|discontinuation)\b.{0,45}\b(?:not established|not appropriate|not supported|not met|unknown)\b',t)
        positive=re.search(r'\bantibiotics?\s+(?:should|can|may|must)\s+(?:be\s+)?(?:stopped|discontinu\w*)\b|\b(?:stop|discontinue)\s+(?:empiri\w*\s+)?antibiotics?\s+(?:at|after|when|by)\b',t)
        if unavailable and (not negative or positive):errors.append('Patient eligibility for stopping is not established; a conditional source rule is not this patient decision')
    if re.search(r'before\s+(?:the\s+)?first\s+(?:antibiotic\s+)?dose',t) and not re.search(r'before\s+(?:giving\s+)?(?:the\s+)?first\s+(?:antibiotic\s+)?dose|before\s+(?:initiating|starting|giving).*antibiotic',quotes):
        errors.append('Cited evidence does not support the pre-dose timing qualifier')
    ga=patient.get('gestational_age_weeks')
    if re.search(r'\b(?:above|below|returned to|higher than|lower than)\s+(?:the\s+)?baseline\b',t) and patient.get('baseline_crp') is None:
        errors.append('Patient baseline is not recorded; do not invent a comparison to baseline')
    if ga is not None and ga<37 and 'among term infants with unexplained critical cardiorespiratory illness' in quotes:
        if re.search(r'continue|justify|justifies|warrant|empiric',t):errors.append('Term-infant exception is not established for this preterm patient; retain its population qualifier')
    if 'NICE' in source:
        if 'moderate-risk' in t or 'moderate risk' in t:errors.append('Unreviewed NICE risk category')
        if re.search(r'(?:tachypn\w*|hypoxi\w*|respiratory distress).{0,90}(?:red.flag)|red.flag.{0,90}(?:tachypn\w*|hypoxi\w*|respiratory distress)',t) and not re.search(r'not.{0,12}red.flag|other clinical indicators',t):
            errors.append('NICE other clinical indicators mislabelled as red flags')
    if 'AAP' in source and re.search(r'category\s*4.{0,65}\badequate\b',t):errors.append('AAP category 4 must not be relabelled adequate prophylaxis')
    if 'WHO' in source:
        cited={s.get('evidence_id') for s in claim['support']}
        parents=' '.join(e['text'] for e in packet.get('evidence',[]) if e['id'] in cited).lower()
        referral_path=bool(re.search(r'referral.{0,35}(?:not feasible|not possible|cannot|refused)',parents))
        regimen=bool(re.search(r'\b(?:ampicillin|amoxicillin|gentamicin)\b',t))
        conditional_action=regimen or claim.get('section') in {'monitoring_plan','follow_up','antibiotic_review'}
        if conditional_action and referral_path and (patient.get('care_setting') in {'hospital','hospital_birth','neonatal_unit'} or patient.get('referral_not_feasible') is not True):
            errors.append('WHO referral-not-feasible regimen does not have established eligibility for this setting')
        if re.search(r'(?:next day|day after).{0,25}starting',t) and not re.search(r'(?:next day|day after).{0,25}starting',quotes):
            errors.append('Cited WHO passage does not support the added review time after starting treatment')
        for drug in ['amoxicillin','ampicillin','gentamicin']:
            if re.search(r'\b'+drug+r'\b',t) and not re.search(r'\b'+drug+r'\b',quotes):errors.append('Drug name absent from cited pathway: '+drug)
        if 'clinical severe infection' in t and re.search(r'any\s+(?:one\s+)?(?:of\s+)?(?:the\s+)?(?:seven|7)\s+sign',t):errors.append('WHO PSBI signs cannot be equated with the clinical-severe-infection subset')
    return errors


def apply_policy(result,packet):
    findings=[];kept=[]
    for c in result['accepted_claims']:
        errors=violations(c,packet,result['patient_fit'])
        if errors:findings.append({'claim_id':c['id'],'reasons':errors})
        else:kept.append(c)
    return kept,findings
