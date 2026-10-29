"""Normalize supported aliases and explicit negation before auditing."""
import re
from rag.patient_application_v13 import states as previous
from rag.offline_repairs_v23 import distress_state,known

def states(packet):
    normalized={**packet,'patient':dict(packet['patient'])};p=normalized['patient']
    if not known(p.get('temperature_c')):p['temperature_c']=next((p.get(k)for k in ['temperature','neonatal_temperature']if known(p.get(k))),None)
    result=previous(normalized)
    if 'NICE_indicator_review'in result:
        result['NICE_indicator_review']['respiratory_distress']['status']=distress_state(p)
    if 'WHO_category_review'in result:
        review=result['WHO_category_review']
        severe=[e for e in packet['evidence']if re.search(r'clinical severe infection is defined',e['text'],re.I)]
        critical=[e for e in packet['evidence']if re.search(r'critical illness is defined',e['text'],re.I)]
        text=' '.join(e['text']for e in severe)
        checks={'high_temperature':r'high (?:body )?temperature.{0,25}38',
                'low_temperature':r'low (?:body )?temperature.{0,25}35[.]5',
                'fast_breathing_age_0_to_6_days':r'0\s*[–-]\s*6\s*days.{0,80}fast breathing.{0,25}60'}
        for field,pattern in checks.items():
            row=review['clinical_severe_infection_signs'][field]
            row['evidence_ids']=[e['id']for e in severe if re.search(pattern,e['text'],re.I)]
            if not re.search(pattern,text,re.I):row['status']='unknown';row['reason']='The matching clinical category threshold is absent from the supplied definition evidence.'
        if not severe:review['clinical_severe_infection_definition_matches']='unknown'
        else:
            values=[v['status']for v in review['clinical_severe_infection_signs'].values()]
            review['clinical_severe_infection_definition_matches']='met'if 'met'in values else'not met'if all(v=='not met'for v in values)else'unknown'
        if not critical:review['critical_illness_definition_matches']='unknown'
        review['definition_evidence_ids']={'clinical_severe_infection':[e['id']for e in severe],'critical_illness':[e['id']for e in critical]}
    return result
