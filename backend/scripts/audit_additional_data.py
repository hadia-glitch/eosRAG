"""Audit supplied synthetic sources without exposing patient rows or changing data."""
import argparse,csv,hashlib,json,statistics
from collections import Counter
from pathlib import Path

POST_OUTCOME={'sepsis_status','sepsis_onset','culture_confirmed','pathogen','outcome','hospital_days','sepsis_probability_score'}

def load(path):
    with path.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    return rows

def numeric(values):
    try:return [float(v) for v in values if v.strip()]
    except ValueError:return None

def audit(path,rows):
    columns={}
    for name in rows[0]:
        values=[r[name] for r in rows];nums=numeric(values)
        entry={'missing':sum(not v.strip() for v in values),'unique':len(set(values))}
        if nums:entry.update(min=min(nums),max=max(nums),median=statistics.median(nums))
        if len(set(values))<=20 and not name.endswith('_id'):entry['counts']=dict(Counter(values))
        columns[name]=entry
    return {'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':len(rows),
        'duplicate_ids':len(rows)-len({r['patient_id'] for r in rows}),'columns':columns,
        'onset_by_label':dict(Counter(f"{r['sepsis_status']} | {r['sepsis_onset']}" for r in rows)),
        'excluded_outcome_or_post_outcome_columns':sorted(POST_OUTCOME),
        'weight_rounding_audit':{'kg_recorded_precision':0.01,'allowed_rounding_difference_grams':5.01,
            'max_absolute_difference_grams':max(abs(float(r['birth_weight_grams'])-float(r['birth_weight_kg'])*1000) for r in rows),
            'within_rounding_tolerance':all(abs(float(r['birth_weight_grams'])-float(r['birth_weight_kg'])*1000)<=5.01 for r in rows)}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--development',type=Path,required=True);p.add_argument('--test',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    development,test=load(a.development),load(a.test)
    names=[k for k in development[0] if k!='patient_id']
    row_key=lambda r:tuple(r[k] for k in names)
    predictors=[k for k in names if k not in POST_OUTCOME]
    key=lambda r:tuple(r[k] for k in predictors)
    report={'synthetic_source':True,'clinical_validation':False,
        'source_url':'https://huggingface.co/datasets/electricsheepafrica/africa-synth-neonatal-sepsis-dataset-all',
        'development':audit(a.development,development),'file_defined_test':audit(a.test,test),
        'overlap':{'shared_ids':len({r['patient_id'] for r in development}&{r['patient_id'] for r in test}),
            'identical_non_id_rows':len({row_key(r) for r in development}&{row_key(r) for r in test}),
            'identical_predictor_vectors':len({key(r) for r in development}&{key(r) for r in test})},
        'limitations':['Synthetic outcomes encode generation assumptions, not measured clinical effectiveness.',
            'No measured assessment/birth/result-availability timestamps establish a prospective prediction landmark.',
            'A synthetic onset label cannot supply missing postnatal ages or outcomes in a different patient cohort.']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
