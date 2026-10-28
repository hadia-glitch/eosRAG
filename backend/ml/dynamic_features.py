"""Shared causal longitudinal design for PIC training and research inference."""
from __future__ import annotations
import math
from typing import Literal
import numpy as np
from pydantic import BaseModel,ConfigDict,Field,model_validator
from ml.dynamic_contract import BOUNDS,VERSION,available_events

FIELDS=tuple(BOUNDS)
SNAPSHOT=('age_hours','sex_female',*(f'{k}__last' for k in FIELDS))
TRENDS=tuple(f'{k}__{s}' for k in FIELDS for s in ['delta','slope_per_hour','minimum','maximum','mean','sd','count','span_hours','recency_hours'])
BINS=tuple(f'{k}__bin{b}' for b in range(6) for k in FIELDS)
GROUPS={'snapshot':SNAPSHOT,'trend':SNAPSHOT+TRENDS,'binned':SNAPSHOT+BINS}


class TimedMeasurement(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    age_hours:float=Field(ge=0,lt=72)
    available_age_hours:float=Field(ge=0,lt=72)
    field:Literal['neonatal_temperature','heart_rate','respiratory_rate','spo2','pulse_rate','diastolic_pressure','systolic_pressure','measured_weight_kg']
    value:float

    @model_validator(mode='after')
    def check(self):
        lo,hi=BOUNDS[self.field]
        if not lo<=self.value<=hi:raise ValueError('Measurement outside documented input units/range')
        if self.available_age_hours<self.age_hours:raise ValueError('Availability precedes measurement')
        return self


class DynamicRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    input_contract_version:Literal['pic-longitudinal-v1']
    purpose:Literal['research']
    age_hours:float=Field(ge=0,lt=72)
    sex:Literal['M','F']|None=None
    observations:list[TimedMeasurement]=Field(min_length=1,max_length=2000)

    @model_validator(mode='after')
    def chronology(self):
        if any(max(e.age_hours,e.available_age_hours)>self.age_hours for e in self.observations):
            raise ValueError('Future or not-yet-available measurement supplied')
        keys=[(e.age_hours,e.field) for e in self.observations]
        if len(keys)!=len(set(keys)):raise ValueError('Duplicate field/time: reconcile before inference')
        return self


def features(index_age,sex,events):
    if type(index_age) not in (int,float) or not math.isfinite(index_age) or not 0<=index_age<72:
        raise ValueError('Prediction age outside neonatal study scope')
    observed=available_events(events,index_age)
    result={'age_hours':index_age,'sex_female':float(sex=='F') if sex in {'F','M'} else None}
    for key in FIELDS:
        # Multiple revisions of one observation cannot masquerade as a trend.
        # Use the last available version, then aggregate conflicting duplicates
        # by their median. The aggregation policy is shared by train and serve.
        by_time={}
        for e in observed:
            if e['field']==key:by_time.setdefault(e['age_hours'],[]).append(float(e['value']))
        pairs=sorted((t,float(np.median(v))) for t,v in by_time.items())
        recent=[(t,v) for t,v in pairs if t>=index_age-6]
        result[f'{key}__last']=recent[-1][1] if recent else None
        result[f'{key}__count']=float(len(pairs))
        for stat in ['delta','slope_per_hour','minimum','maximum','mean','sd','span_hours','recency_hours']:
            result[f'{key}__{stat}']=None
        if pairs:
            t,v=map(np.asarray,zip(*pairs))
            for stat,value in [('minimum',v.min()),('maximum',v.max()),('mean',v.mean()),('sd',v.std()),
                               ('span_hours',t[-1]-t[0]),('recency_hours',index_age-t[-1])]:
                result[f'{key}__{stat}']=float(value)
            if len(pairs)>=2:
                result[f'{key}__delta']=float(v[-1]-v[0])
                result[f'{key}__slope_per_hour']=float(((t-t.mean())*(v-v.mean())).sum()/((t-t.mean())**2).sum())
        for b in range(6):
            lo=index_age-24+4*b;hi=lo+4
            # Left-closed/right-open, except the current index at the final bin.
            bin_pairs=[(t,v) for t,v in pairs if lo<=t<hi or (b==5 and t==index_age)]
            result[f'{key}__bin{b}']=bin_pairs[-1][1] if bin_pairs else None
    return result


def request_features(request):
    return features(request.age_hours,request.sex,[e.model_dump() for e in request.observations])


def design(records,group):
    cols=GROUPS[group]
    extracted=[features(r['index_age_hours'],r['sex'],r['events']) for r in records]
    return np.array([[f[c] for c in cols] for f in extracted],dtype=float)
