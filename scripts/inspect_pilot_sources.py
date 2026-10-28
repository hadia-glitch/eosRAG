"""Compact schema inventory for the supplied Phase 1 evaluation sources."""
import csv, json
from pathlib import Path

BASE=Path.home()/'Downloads'
NAMES=['neoguard_care_plan_eval_dataset_100.json',
 'retrieval_only_metrics (14).csv','generation_evaluation_dense_hybrid.csv',
 'multi_agent_all_arms_results.csv','chunks_clinical_v2.csv',
 'chunks_clinical_v2 (1).csv','chunks_clinical_v2 (2).csv',
 'chunks_clinical_v2 (4).csv','chunks_ingested.csv','grounded (1).json']

def shape(obj):
    if isinstance(obj,dict):return {k:(shape(v) if isinstance(v,(dict,list)) else str(v)[:150]) for k,v in list(obj.items())[:35]}
    if isinstance(obj,list):return {'length':len(obj),'first':shape(obj[0]) if obj else None}
    return str(obj)[:150]

for name in NAMES:
    p=BASE/name
    if not p.exists():continue
    if p.suffix=='.csv':
        rows=list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
        print(json.dumps({'name':name,'rows':len(rows),'columns':list(rows[0]) if rows else [],'first':{k:v[:160] for k,v in rows[0].items()} if rows else {}},ensure_ascii=True))
    else:print(json.dumps({'name':name,'schema':shape(json.loads(p.read_text(encoding='utf-8-sig')))},ensure_ascii=True))
