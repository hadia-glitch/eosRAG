"""Serving contract for the actually trained supplied-label forest.

This separate research endpoint never produces a clinical EOS risk category.
It uses the fitted preprocessing/tree/calibration parameters, without sklearn,
pandas, a rule score or executable serialization in the request path.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path
from typing import Literal,Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from ml.inference import ModelUnavailable, sigmoid

CONTRACT_VERSION = 'supplied-neonatal-input-v1'
# These are input validity bounds, NOT diagnostic thresholds or normal ranges.
FIELDS = [
    ('Gestational_Age','Gestational age','weeks',22,44,True),
    ('Birth_Weight','Birth weight','kg',.2,6.5,True),
    ('Sex','Sex recorded in the dataset','category',None,None,True),
    ('Postnatal_Age','Postnatal age','completed days',0,2,True),
    ('Delivery_Mode','Delivery mode','category',None,None,True),
    ('Apgar','Apgar score','score',0,10,True),
    ('HR','Heart rate','beats/min',0,350,False),
    ('Resp','Respiratory rate','breaths/min',0,150,False),
    ('Temp','Temperature','degrees C',30,43,False),
    ('SpO2','Oxygen saturation','%',20,100,False),
    ('BP','Blood pressure as recorded','mmHg; type unspecified',5,150,False),
    ('Oxygen','Numeric oxygen measurement','dataset units undocumented',0,100,False),
    ('WBC','White blood cell count','dataset units undocumented',0,200,False),
    ('CRP','C-reactive protein','dataset units undocumented',0,600,False),
    ('PCT','Procalcitonin','dataset units undocumented',0,1000,False),
    ('Platelets','Platelet count','dataset units undocumented',0,2000,False),
    ('Lactate','Lactate','dataset units undocumented',0,30,False),
    ('Hemoglobin','Hemoglobin','dataset units undocumented',0,30,False),
]
NUMERIC = [x[0] for x in FIELDS if x[2]!='category']
CATEGORIES = {'Sex':['Female','Male'],'Delivery_Mode':['Cesarean','Vaginal']}
KEYS = {x[0] for x in FIELDS}
BASELINE = {x[0] for x in FIELDS if x[5]}
NOTICE = 'Research supplied-label classifier. This is not a validated probability of clinical early-onset sepsis and must not determine treatment.'


class SuppliedPredictionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    input_contract_version: Literal['supplied-neonatal-input-v1']
    purpose: Literal['research']
    age_hours: float = Field(ge=0,lt=72,strict=True)
    reviewed_inputs: StrictBool
    values: dict[str,Any]

    @model_validator(mode='after')
    def validate_inputs(self):
        if not self.reviewed_inputs:
            raise ValueError('Review the measured values and explicit unknowns before prediction')
        if set(self.values)!=KEYS:
            raise ValueError('The model requires the exact documented feature keys; identifiers and extra fields are rejected')
        for key,label,unit,lo,hi,required in FIELDS:
            value=self.values[key]
            if value is None:
                if required:raise ValueError(f'{key} must be recorded; it was never missing in model development')
                continue
            if key in CATEGORIES:
                if value not in CATEGORIES[key]:raise ValueError(f'Unsupported {key} category')
            elif type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:
                raise ValueError(f'{key} must be a finite numeric measurement in its documented input range')
        if self.values['Postnatal_Age']!=math.floor(self.age_hours/24):
            raise ValueError('Postnatal_Age must be completed days derived from assessment age')
        if self.values['Apgar']!=int(self.values['Apgar']):raise ValueError('Apgar must be an integer')
        return self


class SuppliedModel:
    def __init__(self,a,scope):
        if a.get('feature_version')!='supplied-neonatal-label-research-v1' or a.get('kind') not in {'forest','logistic'} or a.get('clinical_eos_eligible') is not False or a.get('validation_status')!='research_only':
            raise ModelUnavailable('Invalid supplied-label lifecycle metadata')
        if a.get('numeric_columns')!=NUMERIC or a.get('categories')!=CATEGORIES:
            raise ModelUnavailable('Installed research model does not match the input contract')
        names=NUMERIC+[f'{c}={v}' for c,vs in CATEGORIES.items() for v in vs]
        # Training matrix order follows numeric columns then Sex/Delivery_Mode.
        if a.get('features')!=names:raise ModelUnavailable('Research design matrix order mismatch')
        n=len(names)
        for k in ['median','mean','scale']:
            if len(a[k])!=n or not all(math.isfinite(float(v)) for v in a[k]):raise ModelUnavailable('Invalid research preprocessing')
        if any(v<=0 for v in a['scale']):raise ModelUnavailable('Invalid research scaling')
        if not all(math.isfinite(float(a['calibration'][k])) for k in ['slope','intercept']):raise ModelUnavailable('Invalid calibration')
        if a['kind']=='forest':
            if not a.get('trees') or len(a['trees'])>1000:raise ModelUnavailable('Invalid forest size')
            for tree in a['trees']:
                size=len(tree['left'])
                if not 0<size<=100000 or any(len(tree[k])!=size for k in ['right','feature','threshold','probability']):raise ModelUnavailable('Invalid research tree')
                for node in range(size):
                    if not math.isfinite(tree['threshold'][node]) or not 0<=tree['probability'][node]<=1:raise ModelUnavailable('Invalid research tree values')
                    if tree['left'][node]!=-1 and not (0<=tree['feature'][node]<2*n and node<tree['left'][node]<size and node<tree['right'][node]<size):raise ModelUnavailable('Invalid research tree branch')
        elif len(a['coefficients'])!=2*n or not all(math.isfinite(float(v)) for v in [a['intercept'],*a['coefficients']]):raise ModelUnavailable('Invalid logistic coefficients')
        if set(scope.get('ranges',{}))!=set(NUMERIC):raise ModelUnavailable('Missing development support ranges')
        self.a,self.scope,self.names=a,scope,names

    def transform(self,values):
        raw=[values[k] for k in NUMERIC]+[float(values[c]==v) for c,vs in CATEGORIES.items() for v in vs]
        missing=[float(v is None) for v in raw]
        scaled=[((self.a['median'][i] if v is None else v)-self.a['mean'][i])/self.a['scale'][i] for i,v in enumerate(raw)]
        return scaled+missing

    def raw_probability(self,values):
        a=self.a;x=self.transform(values)
        if a['kind']=='forest':
            x=[struct.unpack('f',struct.pack('f',v))[0] for v in x]
            probs=[]
            for t in a['trees']:
                node=0
                while t['left'][node]!=-1:
                    node=t['left'][node] if x[t['feature'][node]]<=t['threshold'][node] else t['right'][node]
                probs.append(t['probability'][node])
            p=sum(probs)/len(probs)
        else:p=sigmoid(a['intercept']+sum(c*v for c,v in zip(a['coefficients'],x)))
        return p

    def probability(self,values):
        p=max(1e-9,min(1-1e-9,self.raw_probability(values)))
        return sigmoid(self.a['calibration']['slope']*math.log(p/(1-p))+self.a['calibration']['intercept'])

    def predict(self,request):
        values=request.values
        missing=[k for k,v in values.items() if v is None]
        outside=[k for k in NUMERIC if values[k] is not None and not self.scope['ranges'][k][0]<=values[k]<=self.scope['ranges'][k][1]]
        reasons=[]
        missing_limit=self.scope.get('max_missing_predictors',0)
        if len(missing)>missing_limit:reasons.append(f'Too many unknown measurements: {len(missing)}; development-matched limit is {missing_limit}')
        if outside:reasons.append('Measurements outside model development support: '+', '.join(outside))
        common={'model_version':self.a['model_version'],'input_contract_version':CONTRACT_VERSION,
                'validation_status':'research_only','clinical_use':False,'target':self.a['target'],
                'missing_features':missing,'missing_fraction':len(missing)/len(KEYS),
                'warnings':[NOTICE,*reasons], 'probability':None,'contributions':[],
                'contribution_method':'median replacement probability difference; not SHAP'}
        if reasons:return {**common,'status':'abstained'}
        p=self.probability(values)
        contributions=[]
        for key in NUMERIC:
            if key=='Postnatal_Age' or values[key] is None:continue
            replaced={**values,key:self.a['median'][self.names.index(key)]}
            contributions.append({'feature':key,'value':values[key],'contribution':p-self.probability(replaced)})
        raw=self.raw_probability(values)
        interpretation='The calibration transform was fitted to the supplied dataset labels. It does not calibrate risk in a clinical EOS population. Source labels, measurement timing and units are unverified.'
        extreme='The calibrated score is near a numerical boundary. This is model saturation, not diagnostic certainty.'
        return {**common,'status':'predicted','probability':p,
                'probability_details':{'raw_model_score':raw,'calibrated_dataset_score':p,
                    'calibration_slope':self.a['calibration']['slope'],
                    'calibration_intercept':self.a['calibration']['intercept'],
                    'interpretation':interpretation,'clinical_probability_available':False,
                    'extreme_score':p<.001 or p>.999},
                'imputed_features':missing,'warnings':[NOTICE,interpretation,*([extreme] if p<.001 or p>.999 else []),*(['Missing measurements were imputed with fit-partition medians: '+', '.join(missing)] if missing else [])],
                'contributions':sorted(contributions,key=lambda c:abs(c['contribution']),reverse=True)[:8]}


@lru_cache(maxsize=2)
def load_supplied_model(folder):
    root=Path(folder)
    try:
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf8'))
        for filename in ['model.json','scope.json']:
            raw=(root/filename).read_bytes()
            if len(raw)>20_000_000 or hashlib.sha256(raw).hexdigest()!=manifest['sha256'][filename]:raise ModelUnavailable('Research artifact digest mismatch')
        return SuppliedModel(json.loads((root/'model.json').read_bytes()),json.loads((root/'scope.json').read_bytes()))
    except (OSError,KeyError,TypeError,ValueError) as exc:
        if isinstance(exc,ModelUnavailable):raise
        raise ModelUnavailable('Trained supplied-label model bundle unavailable or invalid') from exc


def supplied_status(settings):
    try:
        model=load_supplied_model(settings.supplied_model_dir)
        fields=[{'name':key,'label':label,'unit':unit,'minimum':lo,'maximum':hi,'required':required,
                 'categories':CATEGORIES.get(key),'read_only':key=='Postnatal_Age','development_range':model.scope['ranges'].get(key)} for key,label,unit,lo,hi,required in FIELDS]
        return {'available':True,'version':model.a['model_version'],'clinical_ready':False,'validation_status':'research_only',
                'input_contract_version':CONTRACT_VERSION,'input_contract':fields,'notice':NOTICE,'age_scope_hours':[0,72],
                'target':model.a['target'],'dataset_units_verified':False,
                'max_missing_predictors':model.scope.get('max_missing_predictors',0),'missingness_policy':model.scope.get('missingness_policy','')}
    except ModelUnavailable as exc:return {'available':False,'clinical_ready':False,'reason':str(exc)}
