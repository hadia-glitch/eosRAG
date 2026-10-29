"""Render documented observations/unknowns; never create a treatment decision."""
from rag.offline_repairs_v23 import missing_observations,distress_state,clean_numbering
from rag.patient_application_v23 import states
from rag.verification_v6 import patient_fit

def review_context(patient,packet):
    packet={**packet,'patient':patient}
    criteria=patient_fit(packet)
    if distress_state(patient)=='met':
        criteria['clinical_condition_reassuring']={'status':'not met','observed':patient.get('respiratory_distress'),'reason':'Recorded respiratory distress requires clinical reassessment; it is not clinical reassurance.'}
    criteria.update(states(packet))
    missing=missing_observations(patient)
    return criteria,missing

def enrich_plan(plan,patient,packet):
    criteria,missing=review_context(patient,packet)
    lines=[]
    labels={'negative_culture':'Negative culture','culture_incubation_recorded':'Culture incubation recorded','clinical_condition_reassuring':'Clinical condition reassuring','CRP_trend_reassuring':'CRP trend reassuring','RR_and_SpO2':'Respiratory rate and oxygen saturation','site_specific_infection_excluded':'Site-specific infection excluded','unexplained_critical_cardiorespiratory_illness_absent':'Unexplained critical cardiorespiratory illness absent'}
    for key,label in labels.items():
        c=criteria[key]
        observed=''
        if key=='RR_and_SpO2':observed=f'Recorded RR: {patient.get("respiratory_rate","unknown")} breaths/min; SpO2: {patient.get("spo2","unknown")} %. '
        elif key=='CRP_trend_reassuring':observed=f'Recorded current CRP: {patient.get("crp_level","unknown")} mg/L. '
        elif c.get('observed')is not None and not isinstance(c['observed'],dict):observed=f'Recorded: {c["observed"]}'+(' hours. 'if key=='culture_incubation_recorded'else'. ')
        lines.append(f'**{label}: {c["status"].upper()}**. '+observed+c.get('reason','This describes recorded criteria, not eligibility to stop treatment.'))
    plan.plan_sections[0].title='Assessment scope and uncertainty'
    plan.plan_sections[0].items.extend(['Clinical judgement / recorded criteria: '+line for line in lines])
    if missing:
        note='Clinical judgement — do now: obtain missing bedside observations: '+', '.join(missing)+'. Missing findings do not establish reassurance or suitability for home observation.'
        plan.recommended_actions.insert(0,note);plan.plan_sections[5].items.insert(0,note)
    for section in plan.plan_sections:
        if section.status in {'withheld','not_determined'}and not any('Not supported by retrieved evidence'in t for t in section.items):section.items.insert(0,'Not supported by retrieved evidence')
        if section.id in {'S06','S08','S09','S10'}:section.items=clean_numbering(section.items)
    plan.plan_sections[11].items.append('Clinical judgement — caregiver note: The neonatal team is reviewing the observations and results. Ask the bedside team to explain the current concerns and next review. This output does not establish that infection has been excluded.')
    plan.risk_analysis+='\n\n**Recorded criteria and clinical judgement**\n'+'\n'.join(lines)
    plan.antibiotic_plan.stop_criteria+=' '+' '.join(line.replace('**','')for line in lines)
    plan.resolution_log.append('Patient criteria remain met / not met / unknown; these checks do not authorize stopping or discharge.')
    return plan
