"""Offline candidate fixes; never grants a new evidence approval."""
import copy,re,math
UNKNOWN={'','unknown','not documented','not recorded','unavailable','not determined','none provided'}

def known(value):
    if value is None:return False
    if isinstance(value,str):return value.strip().lower()not in UNKNOWN
    if isinstance(value,float):return math.isfinite(value)
    return True

def missing_observations(patient):
    aliases={'feeding':['feeding','feeding_status','feeding_tolerance'],'movement':['movement','neurological_status'],
             'temperature':['temperature_c','temperature','neonatal_temperature'],
             'breathing':['respiratory_rate','respiratory_distress'],'oxygen saturation':['spo2','oxygen_saturation']}
    return [name for name,fields in aliases.items()if not any(known(patient.get(f))for f in fields)]

def distress_state(patient):
    explicit=patient.get('respiratory_distress')
    if explicit is True:return 'met'
    if explicit is False:return 'not met'
    text=str(explicit if known(explicit)else patient.get('clinical_condition','')).strip().lower()
    if re.search(r'\b(?:no|without|absent|denies|not)\s+(?:signs of\s+)?respiratory distress\b',text)or text in {'absent','none','false','no'}:return 'not met'
    if 'respiratory distress'in text or text in {'present','true','yes','mild','severe'}:return 'met'
    return 'unknown'

def clean_numbering(items):
    return [f'{i}. '+re.sub(r'^(?:\s*\d+\.\s+)+','',text).strip()for i,text in enumerate(items,1)]

def repair_rendering(saved_result,packet):
    result=copy.deepcopy(saved_result);missing=missing_observations(packet['patient'])
    result['uncertainty']['missing_bedside_observations']=missing
    if 'temperature_c_assessed'in result.get('patient_fit',{}):
        value=next((packet['patient'].get(k)for k in ['temperature_c','temperature','neonatal_temperature']if known(packet['patient'].get(k))),None)
        result['patient_fit']['temperature_c_assessed']={'status':'met'if known(value)else'unknown','observed':value,'reason':'A recorded temperature assessment is distinct from an abnormal temperature sign.'}
        result['uncertainty']['criteria']=result['patient_fit']
        if 'temperature_c_assessed'in result.get('patient_application',{}):result['patient_application']['temperature_c_assessed']=result['patient_fit']['temperature_c_assessed']
    if 'NICE_indicator_review'in result.get('patient_application',{}):
        result['patient_application']['NICE_indicator_review']['respiratory_distress']['status']=distress_state(packet['patient'])
    # Regenerate only the known "obtain missing observations" helper lines. Source
    # words, clinical audit decisions and the original completeness gate stay fixed.
    for section in result['plan_sections']:
        if 'patient_application'in section:section['patient_application']=result['patient_application']
        revised=[]
        for item in section['items']:
            if re.match(r'^(?:\d+\.\s*)*(?:Recorded context / clinical judgement|Clinical judgement) ',item):
                item=item.replace('\u00e2\u20ac\u201d','\u2014',1)
            if 'do now: obtain missing bedside observations:'in item:
                item='Clinical judgement — do now: '+('obtain missing bedside observations: '+', '.join(missing)if missing else 'review the recorded clinical condition and ongoing concerns with the neonatal clinician')+'.'
            elif 'obtain the missing bedside examination and observations:'in item:
                if not missing:continue
                item='Clinical judgement — do now: obtain the missing bedside examination and observations: '+', '.join(missing)+'. Unknown observations do not establish suitability for home observation.'
            # The first section embeds the same uncertainty object as JSON.
            if section['id']=='S01'and 'missing_bedside_observations'in item:
                import json
                item='Recorded context / clinical judgement: '+json.dumps(result['uncertainty'],ensure_ascii=False)
            revised.append(item)
        section['items']=clean_numbering(revised)if section['id']in {'S06','S08','S09','S10'}else revised
    result['offline_repair']={'fresh_model_calls':0,'new_evidence_approvals':0,'original_decisions_retained':True,'version':'rendering-v23'}
    return result
