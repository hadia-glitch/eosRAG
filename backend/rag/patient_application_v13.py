"""Explicit observed/unknown criterion states; no invented numerical NICE cutoff."""
import re,math


def boolean(value):
    return 'met' if value is True else 'not met' if value is False else 'unknown'


def states(packet):
    p=packet['patient'];result={};evidence=packet['evidence'];source=' '.join(e['text'] for e in evidence)
    if 'NICE' in packet.get('guideline','').upper():
        indicators={}
        for field in ['apnoea','seizures','need_for_cpr','mechanical_ventilation','signs_of_shock']:
            indicators[field]={'status':boolean(p.get(field)),'guideline_category':'red flag clinical indicator','observed':p.get(field)}
        distress=p.get('respiratory_distress');condition=str(p.get('clinical_condition',''))
        documented=distress is True or (isinstance(distress,str) and distress.lower() not in {'none','unknown','not recorded'}) or bool(re.search('respiratory distress',condition,re.I))
        indicators['respiratory_distress']={'status':'met' if documented else 'not met' if distress is False else 'unknown','guideline_category':'other clinical indicator','observed':distress or p.get('clinical_condition')}
        for name,field in [('tachypnoea','respiratory_rate'),('hypoxia','spo2')]:
            indicators[name]={'status':boolean(p.get('documented_'+name)),'guideline_category':'other clinical indicator','observed':p.get(field),'reason':'Recorded value shown; no universal numerical NICE threshold is invented. Clinical interpretation is required.'}
        result['NICE_indicator_review']=indicators
    if 'WHO' in packet.get('guideline','').upper():
        temp=p.get('temperature_c',p.get('neonatal_temperature'));rr=p.get('respiratory_rate');age=p.get('age_hours')
        numeric=lambda v:type(v) in (int,float) and math.isfinite(v)
        critical={k:{'status':boolean(p.get(k)),'observed':p.get(k)} for k in ['unable_to_feed_at_all','no_movement_on_stimulation','convulsions']}
        severe={k:{'status':boolean(p.get(k)),'observed':p.get(k)} for k in ['not_feeding_well','movement_only_when_stimulated','severe_chest_indrawing']}
        severe['high_temperature']={'status':boolean(temp>=38) if numeric(temp) and re.search(r'38',source) else 'unknown','observed':temp}
        severe['low_temperature']={'status':boolean(temp<35.5) if numeric(temp) and '35.5' in source else 'unknown','observed':temp}
        defined=bool(re.search(r'0\s*[–-]\s*6\s*days',source)) and bool(re.search(r'60',source))
        severe['fast_breathing_age_0_to_6_days']={'status':boolean(rr>=60) if defined and numeric(rr) and numeric(age) and 0<=age<168 else 'not met' if numeric(age) and age>=168 else 'unknown','observed':{'age_hours':age,'respiratory_rate':rr},'reason':'This additional CSI sign is age-specific, not an equivalence between seven PSBI signs and CSI.'}
        any_status=lambda items:'met' if any(x['status']=='met' for x in items.values()) else 'not met' if all(x['status']=='not met' for x in items.values()) else 'unknown'
        result['WHO_category_review']={'critical_illness_signs':critical,'clinical_severe_infection_signs':severe,
            'critical_illness_definition_matches':any_status(critical),'clinical_severe_infection_definition_matches':any_status(severe),
            'diagnosis_or_treatment_authorized':False,'reason':'Separate source-defined subsets are reviewed. A matching sign does not establish a final diagnosis, and unknown critical signs must still be examined.'}
    result['treatment_pathway_review']={'referral_unavailable':{'status':'not met' if p.get('referral_possible') is True else 'met' if p.get('referral_possible') is False else 'unknown','observed':p.get('referral_possible')},
        'pre_first_dose_opportunity':{'status':'not met' if (p.get('antibiotic_exposure_hours',p.get('antibiotic_duration_hours')) or 0)>0 else 'unknown','reason':'Unknown treatment status is not proof the first dose has not been given.'}}
    return result
