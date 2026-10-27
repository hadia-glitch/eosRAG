"""Run the same preregistered four variants on the v2 source-heading index."""
import argparse
import json
import copy
from backend.scripts import evaluate_rag_improvements as study
from backend.scripts import resume_retrieval_cached as cached
from rag.relevance import focus_query

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);a=p.parse_args()
    study.OUT=study.ROOT/'output/research/rag_improvement_v2'
    study.OLD=study.OUT/'inputs'
    # AAP and WHO representations are unchanged. Exact-input reuse across
    # study directories avoids rerunning identical deterministic retrieval.
    prior=study.ROOT/'output/research/rag_improvement_v1/retrieval'/a.model.replace('/','__')
    old_corpus=json.loads((study.ROOT/'output/research/expanded100/corpus.json').read_text())['chunks']
    cases={c['id']:c['query'] for c in json.loads((study.OLD/'cases.json').read_text())}
    old_by_source={g:[c for c in old_corpus if c['guideline_id']==g] for g in ['NICE','AAP','WHO']}
    original=study.search
    def unchanged(query,texts,bm,encoder,vectors,reranker,config,model):
        for g,chunks in old_by_source.items():
            if texts!=[c['text'] for c in chunks]:continue
            byid={c['chunk_id']:i for i,c in enumerate(chunks)}
            for path in prior.glob('*.json'):
                row=json.loads(path.read_text())
                if 'rankings' not in row or row['guideline']!=g:continue
                if focus_query(cases[row['id']])==focus_query(query):
                    return {v:[byid[k] for k in ids] for v,ids in row['rankings'].items()}
        return original(query,texts,bm,encoder,vectors,reranker,config,model)
    study.search=unchanged
    cached.main(a.model)
