"""Search facets from prevalidated chronological measurements, not risk rules."""
import math


def observed_queries(patient,history):
    labels={'respiratory_rate':'respiratory rate','spo2':'oxygen saturation',
            'crp_level':'C-reactive protein','neonatal_temperature':'body temperature'}
    rows=[r.get('measurements',{}) for r in history]+[patient]
    queries=[];directions={}
    for key,label in labels.items():
        values=[r[key] for r in rows if type(r.get(key)) in (int,float) and math.isfinite(r[key])]
        if len(values)<2 or values[-1]==values[0]:continue
        direction='increasing' if values[-1]>values[0] else 'decreasing'
        directions[key]=direction
        queries.append(f'serial {label} {direction} guideline interpretation clinical condition reassessment')
    if directions.get('crp_level')=='decreasing' and (
        directions.get('respiratory_rate')=='increasing' or directions.get('spo2')=='decreasing'):
        queries.append('opposing inflammatory marker and respiratory measurement trends interpret with clinical assessment and investigation results')
    return queries
