"""Larger cross-encoder ablation on fixed candidates. Development only."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from rag.rank_fusion import fuse_rankings
from rag.faceted_selection import select_facets
from rag.guidance_lanes import guidance_role
from rag.relevance import focus_query,passage_windows
from scripts.evaluate_rag_improvements import save

OUT=ROOT/'output/research/rag_development/bge_reranker'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    import torch
    from transformers import AutoModelForSequenceClassification,AutoTokenizer
    torch.set_num_threads(4)
    data=ROOT/'output/research/rag_development'
    inputs=sorted((data/'listwise/runs').glob('*.json'))
    if len(inputs)!=100:raise ValueError('Incomplete candidate study')
    corpus=[c for c in json.loads((data/'medcpt/corpus.json').read_text())['chunks'] if guidance_role(c)]
    byid={c['chunk_id']:i for i,c in enumerate(corpus)}
    case_queries={c['id']:focus_query(c['query']) for c in json.loads((ROOT/'output/research/expanded100/cases.json').read_text())}
    owners=[]
    for i,c in enumerate(corpus):owners.extend([i]*len(passage_windows(c['raw_text'])))
    with np.load(data/'faceted/embedding_cache/documents.npz') as a:matrix=a['medical']
    owners=np.array(owners);vectors=np.array([matrix[owners==i].mean(axis=0) for i in range(len(corpus))])
    protocol={'stage':'development_only','final_evaluation':False,'model':'BAAI/bge-reranker-v2-m3',
        'model_inputs':'Original focused question and full candidate passages scored in 180-word/40-overlap windows.',
        'candidate_budget':24,'rrf_k':60,'mmr_diversity':.15,'depths':[4,8],
        'methods':['bge_only','bge_upstream_rrf_mmr','bge_consensus_rrf_mmr'],
        'comparison':'Fixed candidate pool, frozen model weights; no labels or reference answers enter ranking.',
        'code_sha256':{p:sha(ROOT/p) for p in ['backend/scripts/develop_bge_reranker.py','backend/rag/faceted_selection.py']},
        'corpus_sha256':sha(data/'medcpt/corpus.json'),
        'input_sha256':{p.name:sha(p) for p in inputs}}
    p=OUT/'development_protocol.json'
    if p.exists() and json.loads(p.read_text())!=protocol:raise ValueError('BGE protocol drift')
    save(p,protocol)
    print('Loading frozen BGE cross encoder (development only)',flush=True)
    tokenizer=AutoTokenizer.from_pretrained(protocol['model'])
    model=AutoModelForSequenceClassification.from_pretrained(protocol['model']).eval()
    save(OUT/'model_revision.json',{'model':protocol['model'],'revision':model.config._commit_hash,
        'torch':torch.__version__,'device':'cpu','threads':4,'dtype':str(next(model.parameters()).dtype),
        'max_sequence_length':512,'training':False,'seed':'No stochastic inference sampling; fixed frozen model in eval mode.'})
    cache={}
    for p in inputs:
        r=json.loads(p.read_text());target=OUT/'runs'/p.name
        if target.exists():continue
        query=case_queries[r['id']];ids=r['candidate_ids'];key=hashlib.sha256(json.dumps([query,ids]).encode()).hexdigest()
        stored=OUT/'score_cache'/f'{key}.json'
        if key not in cache:
            if stored.exists():scores=json.loads(stored.read_text())['scores']
            else:
                pairs=[];owner=[]
                for i,cid in enumerate(ids):
                    c=corpus[byid[cid]];h=c.get('retrieval_headings',{})
                    title=' / '.join(v for v in [h.get('parent_heading'),h.get('section_heading')] if v)
                    for span in passage_windows(c['raw_text']):pairs.append([query,title+' / '+span]);owner.append(i)
                values=[]
                with torch.inference_mode():
                    for start in range(0,len(pairs),4):
                        encoded=tokenizer(pairs[start:start+4],padding=True,truncation=True,max_length=512,return_tensors='pt')
                        values.extend(model(**encoded).logits.reshape(-1).float().tolist())
                if len(values)!=len(pairs) or not np.isfinite(values).all():raise ValueError('Invalid BGE scores')
                scores=[max(v for v,o in zip(values,owner) if o==i) for i in range(len(ids))]
                save(stored,{'query':query,'candidate_ids':ids,'scores':scores})
            ordered=[cid for cid,s in sorted(zip(ids,scores),key=lambda v:(-v[1],v[0]))]
            cache[key]=ordered
        ordered=cache[key]
        previous=json.loads((data/'consensus/runs'/p.name).read_text())['rankings']['8']
        ranks={}
        for name,order in [('bge_only',ordered),('bge_upstream_rrf_mmr',fuse_rankings([ids,ordered],60)),
                           ('bge_consensus_rrf_mmr',fuse_rankings([previous,ordered],60))]:
            ranks[name]={str(k):([corpus[i]['chunk_id'] for i in select_facets([byid[c] for c in order],vectors,k)]
                                 if name!='bge_only' else order[:k]) for k in protocol['depths']}
        save(target,{'id':r['id'],'guideline':r['guideline'],'family':r['family'],'rankings':ranks,
            'candidate_ids':ids,'stage':'development_only','new_groq_calls':0})
        print('BGE development',r['id'],flush=True)
    print('BGE development complete; no final answer evaluation started.',flush=True)


if __name__=='__main__':main()
