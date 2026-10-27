"""Expose source-ID collisions without changing the frozen pilot or gold."""
import ast,csv,hashlib,json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/research/phase1_pilot'

def main():
    x=json.loads((OUT/'inputs.json').read_text());groups=defaultdict(list)
    with (Path.home()/'Downloads/chunks_ingested.csv').open(encoding='utf-8-sig',newline='') as f:
        for row_number,row in enumerate(csv.DictReader(f),2):groups[row['chunk_id']].append((row_number,row))
    collisions=[];affected=set()
    for cid,variants in groups.items():
        if len(variants)<2:continue
        cases=[]
        for case in x['cases']:
            retrieved={i for r in x['retrieval'] if r['case_id']==case['case_id'] for i in ast.literal_eval(r['retrieved_chunk_ids'])[:10]}
            if cid in retrieved or cid in case['gold_chunk_ids']:cases.append(case['case_id'])
        affected.update(cases)
        assert x['corpus'][cid]==variants[-1][1]
        collisions.append({'chunk_id':cid,'distinct_texts':len({r['chunk_text'] for _,r in variants}),
            'affected_selected_cases':cases,'frozen_selected_row':variants[-1][0],
            'variants':[{'csv_row':n,**r,'text_sha256':hashlib.sha256(r['chunk_text'].encode()).hexdigest()} for n,r in variants]})
    result={'source_rows':sum(len(v) for v in groups.values()),'distinct_ids':len(groups),
        'duplicate_id_groups':len(collisions),'conflicting_text_groups':sum(c['distinct_texts']>1 for c in collisions),
        'selected_colliding_ids':sum(bool(c['affected_selected_cases']) for c in collisions),
        'affected_selected_case_ids':sorted(affected),'frozen_resolution':'Last CSV occurrence per identifier, exactly matching the already frozen inputs.json; not independent source adjudication.',
        'original_inputs_or_gold_modified':False,
        'interpretation':'Exact ID scores cannot disambiguate conflicting passage identity. Semantic/source judgments are conditional on the frozen last-row texts. Source identity must be resolved before expansion or a confirmatory comparison.',
        'collisions':collisions}
    (OUT/'source_id_collision_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='collisions'}))

if __name__=='__main__':main()
