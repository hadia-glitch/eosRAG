"""Thirteen review sections; absent evidence stays explicitly undetermined."""

MEASUREMENTS={
    'culture_status':('Recorded culture status',''),
    'culture_incubation_hours':('Recorded culture incubation','hours'),
    'antibiotic_exposure_hours':('Recorded neonatal antibiotic exposure','hours'),
    'age_hours':('Postnatal age','hours'),'gestational_age_weeks':('Gestational age','weeks'),
    'birth_weight_g':('Birth weight','g'),'heart_rate':('Heart rate','beats/min'),
    'respiratory_rate':('Respiratory rate','breaths/min'),'spo2':('Oxygen saturation','%'),
    'neonatal_temperature':('Temperature','degrees C'),'crp_level':('CRP','mg/L'),
    'wbc_count':('White blood cells','cells/mm3'),'platelet_count':('Platelets','cells/mm3'),
    'pct_level':('Procalcitonin','ng/mL'),'creatinine_mg_dl':('Creatinine','mg/dL'),
    'respiratory_distress':('Recorded respiratory distress',''),
    'oxygen_need':('Recorded oxygen support',''),'neurological_status':('Recorded neurological status','')}

SECTION_GAPS={
    'risk_analysis':'No risk interpretation passed both evidence reviews. Recorded observations remain available above.',
    'recommended_actions':'No patient-specific action passed both reviews. Review the observed findings with the responsible neonatal clinician.',
    'investigations':'Investigation recommendations were not supported by the retrieved evidence. Record culture sampling, results and treatment timing before a treatment review.',
    'antibiotic_review':'A treatment decision has not been made by this app. Confirm the local formulary, allergy history, cultures and renal information with the prescriber.',
    'monitoring_plan':'An individual monitoring schedule needs the bedside assessment and local neonatal observation protocol.',
    'escalation_criteria':'A case-specific escalation recommendation was not released. Do not interpret the missing recommendation as reassurance.',
    'nutrition_fluids':'Feeding tolerance, glucose, fluid balance and the local neonatal fluid pathway are needed for an individual nutrition/fluid plan. This evidence packet does not authorize fluid prescriptions.',
    'parent_communication_notes':'Record what has been discussed with parents or carers, their questions and the agreed next review.',
    'follow_up':'Record the named reviewing clinician, pending results and next review time. Discharge eligibility has not been established.'}

def build_sections(patient,trend,claims,supported):
    sections=[]
    def add(title,items,status='recorded',labels=None):
        sections.append({'id':f'S{len(sections)+1:02d}','title':title,'status':status,
                         'items':items,'evidence_labels':labels or []})
    def generated(title,key):
        selected=[c for c in claims if c['section']==key] if supported else []
        items=[c['text']+' '+' '.join(f"[{s['evidence_id']}]" for s in c['support']) for c in selected]
        if items and key=='antibiotic_review':
            items.insert(0,'This review does not establish eligibility to stop treatment. The following are conditional guideline options for prescriber review, not a medication order.')
            if patient.get('culture_incubation_hours') is None or patient.get('antibiotic_exposure_hours') is None:
                items.insert(1,'Culture incubation and neonatal antibiotic exposure are separate time fields. Missing durations are unknown; postnatal age is not a substitute.')
        labels=sorted({s['evidence_id'] for c in selected for s in c['support']})
        add(title,items or [SECTION_GAPS[key]],
            'evidence_supported' if items else 'not_determined' if supported else 'withheld',labels)
    add('Assessment scope',['Early-onset neonatal infection evidence discussion for clinician review.',
                            'Automated recommendations '+('passed source and safety checks; they require clinical review.' if supported else 'are withheld.')])
    measurements=[f'{label}: {patient[key]} {unit}'.strip() for key,(label,unit) in MEASUREMENTS.items() if patient.get(key) is not None]
    add('Recorded patient measurements',measurements or ['No allowlisted measurements were recorded.'])
    add('Longitudinal observations',[trend])
    add('Prediction status',['No validated clinical EOS probability is supplied by the language model. Research supplied-label predictions remain separate in the Risk tab.'])
    generated('Evidence-supported risk discussion','risk_analysis')
    generated('Immediate clinical considerations','recommended_actions')
    generated('Investigations','investigations')
    generated('Antibiotic review','antibiotic_review')
    generated('Monitoring','monitoring_plan')
    generated('Escalation','escalation_criteria')
    generated('Nutrition and fluids','nutrition_fluids')
    generated('Parent communication','parent_communication_notes')
    generated('Follow-up and handover','follow_up')
    return sections
