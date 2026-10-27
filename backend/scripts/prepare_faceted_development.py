"""Preserve old query outcomes; revalidate known system-scope age wording."""
import json
import hashlib
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from rag.query_plan_validation import validate_questions
from rag.guidance_lanes import guidance_role
from scripts.evaluate_rag_improvements import save

OUT=ROOT/'output/research/rag_development/faceted'

if __name__=='__main__':
    if (OUT/'preparation.json').exists():raise SystemExit('Faceted development already prepared; refusing overwrite')
    old=ROOT/'output/research/rag_development/query_planning/plans'
    accepted=0;count=0
    for path in sorted(old.glob('*.json')):
        row=json.loads(path.read_text())
        response=next((c['response'] for c in reversed(row['calls']) if 'response' in c),{})
        questions=response.get('questions',[])
        valid,reason=validate_questions(questions,row['query'])
        save(OUT/'plans'/path.name,{'source':row['source'],'query':row['query'],'available':valid,
             'questions':questions if valid else [row['query']],'validation_reason':reason,
             'original_plan_available':row['available'],'original_record_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'amendment':'Only the explicit EOS system age scope is recognized; no model answer is regenerated.'})
        accepted+=valid;count+=1
    corpus=json.loads((ROOT/'output/research/rag_development/medcpt/corpus.json').read_text())
    roles={c['chunk_id']:'guidance' if guidance_role(c) else 'background' for c in corpus['chunks']}
    save(OUT/'source_roles.json',roles)
    save(OUT/'preparation.json',{'plans':count,'valid_plans':accepted,'invalid_plans':count-accepted,
         'clinical_review':'pending','stage':'development_only','final_evaluation':False,
         'guidance_counts':{g:sum(c['guideline_id']==g and roles[c['chunk_id']]=='guidance' for c in corpus['chunks']) for g in ['NICE','AAP','WHO']}})
    print('Plans:',accepted,'/',count,'validated; source roles saved')
