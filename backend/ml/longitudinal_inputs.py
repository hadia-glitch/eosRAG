"""Research longitudinal input alignment requested after the RAG-only instruction.

Input validation and preview do not install a clinical predictor. The new PIC
candidate fails the quality gate and its score must not be used as clinical risk.
"""
from __future__ import annotations
import math
from pydantic import BaseModel,ConfigDict,model_validator
from ml.dynamic_contract import BOUNDS,VERSION
from ml.dynamic_features import DynamicRequest,features,FIELDS

# key: label, unit, min, max, synthetic model input (otherwise guideline context)
CONTEXT={
    'gestational_age_weeks':('Gestational age','weeks',22,44,True),
    'birth_weight_kg':('Birth weight','kg',.2,6.5,True),
    'maternal_age':('Maternal age','years',10,60,True),
    'maternal_temperature':('Highest intrapartum maternal temperature','°C',30,43,False),
    'rom_hours':('Duration of membrane rupture','hours',0,336,False),
    'prom':('Prolonged rupture of membranes recorded','boolean',None,None,True),
    'gbs_positive':('Maternal GBS positive','boolean',None,None,False),
    'adequate_intrapartum_antibiotics':('Adequate intrapartum antibiotics recorded','boolean',None,None,False),
    'clinical_chorioamnionitis':('Clinical chorioamnionitis recorded','boolean',None,None,False),
    'maternal_infection':('Maternal infection recorded','boolean',None,None,True),
    'cesarean':('Cesarean birth','boolean',None,None,True),
    'apgar_1min':('Apgar at 1 minute','score',0,10,True),
    'apgar_5min':('Apgar at 5 minutes','score',0,10,True),
    'resuscitation_needed':('Resuscitation needed','boolean',None,None,True),
    'fever':('Fever recorded','boolean',None,None,True),
    'hypothermia':('Hypothermia recorded','boolean',None,None,True),
    'respiratory_distress':('Respiratory distress recorded','boolean',None,None,True),
    'poor_feeding':('Poor feeding recorded','boolean',None,None,True),
    'lethargy':('Lethargy recorded','boolean',None,None,True),
    'jaundice':('Jaundice recorded','boolean',None,None,True),
}
LABELS={'neonatal_temperature':('Temperature','°C'),'heart_rate':('Heart rate','beats/min'),
        'respiratory_rate':('Respiratory rate','breaths/min'),'spo2':('SpO₂','%'),
        'pulse_rate':('Pulse rate','beats/min'),'systolic_pressure':('Systolic pressure','mmHg'),
        'diastolic_pressure':('Diastolic pressure','mmHg'),'measured_weight_kg':('Measured weight','kg')}


class LongitudinalInputs(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    sequence:DynamicRequest
    context:dict[str,float|bool|None]

    @model_validator(mode='after')
    def check(self):
        if set(self.context)!=set(CONTEXT):raise ValueError('Use the exact context keys; missing observations must be null')
        for key,(_,unit,lo,hi,_) in CONTEXT.items():
            value=self.context[key]
            if value is None:continue
            if unit=='boolean':
                if type(value) is not bool:raise ValueError(f'{key} must be true, false or null')
            elif type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:
                raise ValueError(f'{key} outside documented units/range')
            if key.startswith('apgar') and value!=int(value):raise ValueError('Apgar scores must be integers')
        return self


def contract():
    return {'input_contract_version':VERSION,'purpose':'research','clinical_ready':False,
        'sequence_fields':[{'key':k,'label':LABELS[k][0],'unit':LABELS[k][1],'min':lo,'max':hi} for k,(lo,hi) in BOUNDS.items()],
        'context_fields':[{'key':k,'label':label,'unit':unit,'min':lo,'max':hi,
            'use':'Synthetic model input; recorded guideline context' if synthetic else 'Recorded guideline context; no trained maternal coefficient available'}
            for k,(label,unit,lo,hi,synthetic) in CONTEXT.items()],
        'prediction_status':'withheld_quality_gate','scope':'Research in hospital neonates below 72 hours',
        'reason':'PIC candidate has too few independent infections and inadequate cross-validated discrimination.',
        'unknowns':'Null is unknown. Missing maternal values are never replaced with false or normal.',
        'fusion':'No joint EOS probability: real PIC observations and synthetic maternal records are not linked patients.'}


def preview(request):
    events=[e.model_dump() for e in request.sequence.observations]
    f=features(request.sequence.age_hours,request.sequence.sex,events)
    return {'status':'inputs_validated_prediction_withheld','clinical_ready':False,
        'prediction_status':'withheld_quality_gate','research_score':None,
        'age_hours':request.sequence.age_hours,'recorded_measurement_count':len(events),
        'trends':{k:{s:f[k+'__'+s] for s in ['last','count','delta','slope_per_hour','recency_hours']} for k in FIELDS},
        'context_usage':{k:{'recorded':v is not None,'used_in_real_pic_model':False,
            'available_in_synthetic_training':CONTEXT[k][4],'available_for_guideline_context':v is not None}
            for k,v in request.context.items()},
        'missing_synthetic_inputs':[k for k,v in request.context.items() if v is None and CONTEXT[k][4]],
        'notice':'Observed trends are measurements, not a diagnosis. The new PIC candidate is withheld because development performance is inadequate. Synthetic maternal modelling does not establish real-patient EOS risk.'}
