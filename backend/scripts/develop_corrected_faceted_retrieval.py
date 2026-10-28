"""Guidance-lane and multi-intent development ablations. No final generation.

Both 4-passage and larger evidence budgets are reported; added context is never
counted as if it occupied an original top-four slot. Golds are scoring-only.
"""
import hashlib
import json
import re
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
OUT=ROOT/'output/research/rag_development/recommendation_units/faceted'
from rag.clinical_scope import applicable
from rag.relevance import focus_query,passage_windows,rerank_scores
from rag.guidance_lanes import guidance_role
from rag.selection import expand_query
from rag.rank_fusion import fuse_rankings
from rag.faceted_selection import select_facets
from scripts.develop_query_plans import plan_key
from scripts.develop_medical_retrieval import explicit_edges
from scripts.evaluate_rag_improvements import save


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import torch
    from sentence_transformers import SentenceTransformer,CrossEncoder
    from rank_bm25 import BM25Okapi
    from rag.medical_models import MedCPT
    torch.set_num_threads(4)
    source=ROOT/'output/research/rag_development/recommendation_units/corpus.json'
    casesfile=ROOT/'output/research/expanded100/cases.json'
    cases=json.loads(casesfile.read_text())
    routes={r['id']:r['guideline'] for r in json.loads((ROOT/'output/research/expanded100/manifest.json').read_text())['cases']}
    all_chunks=json.loads(source.read_text())['chunks']
    chunks=[c for c in all_chunks if guidance_role(c)]
    texts=[c['text'] for c in chunks];byid={c['chunk_id']:i for i,c in enumerate(chunks)}
    conflicts=[{'id':c['id'],'excluded_gold':[g for g in c['gold_chunk_ids'] if g not in byid]} for c in cases]
    save(OUT/'role_gold_audit.json',conflicts)
    if any(r['excluded_gold'] for r in conflicts):raise ValueError('Source role/gold conflict requires adjudication; no labels changed')
    config={'stage':'development_only','final_evaluation':False,'cases_sha256':sha(casesfile),'corpus_sha256':sha(source),
        'guidance_lane':'Publisher recommendation/scope spans; AAP clinical risk-assessment, laboratory, treatment and summary sections',
        'source_boundary_amendment_sha256':sha(source.parent/'corpus_protocol.json'), 'api_calls':0, 'source_counts':{g:sum(c['guideline_id']==g for c in chunks) for g in ['NICE','AAP','WHO']},
        'models':['ncbi/MedCPT','sentence-transformers/all-MiniLM-L6-v2'],
        'rerankers':['ncbi/MedCPT-Cross-Encoder','cross-encoder/ms-marco-MiniLM-L-6-v2'],
        'methods':['generic_single','medical_single','generic_faceted','medical_faceted','medical_faceted_graph'],
        'depths':[1,2,4,6,8,12],'rrf_k':60,'candidate_limit':60,'mmr_diversity':.15,
        'graph':'Forward and reverse explicit recommendation references; candidate expansion, no uniform graph-degree boost',
        'plans_sha256':{p.name:sha(p) for p in sorted((OUT/'plans').glob('*.json'))},
        'code_sha256':{p:sha(ROOT/p) for p in ['backend/scripts/develop_corrected_faceted_retrieval.py','backend/rag/faceted_selection.py',
            'backend/rag/guidance_lanes.py','backend/rag/clinical_scope.py','backend/rag/medical_models.py']}}
    p=OUT/'development_protocol.json'
    if p.exists() and json.loads(p.read_text())!=config:raise ValueError('Frozen faceted config drift')
    save(p,config)
    medical=MedCPT();generic=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    generic.max_seq_length=512
    ce=CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    save(OUT/'model_revisions.json',medical.revisions)
    owners=[];spans=[];pairs=[]
    for i,c in enumerate(chunks):
        title=' / '.join(s for s in [c['source'],c.get('retrieval_headings',{}).get('parent_heading'),
                                   c.get('retrieval_headings',{}).get('section_heading')] if s)
        for text in passage_windows(c['raw_text']):
            owners.append(i);pairs.append([title,text]);spans.append(title+' / '+text)
    cachefile=OUT/'embedding_cache/documents.npz'
    if cachefile.exists():
        with np.load(cachefile) as a:mv=a['medical'];gv=a['generic']
    else:
        mv=medical.article_vectors(pairs);gv=generic.encode(spans,normalize_embeddings=True,show_progress_bar=False)
        cachefile.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(cachefile,medical=mv,generic=gv)
    owners=np.array(owners)
    mm=np.array([mv[owners==i].mean(axis=0) for i in range(len(chunks))])
    gm=np.array([gv[owners==i].mean(axis=0) for i in range(len(chunks))])
    edges=explicit_edges(chunks);reverse={i:set() for i in byid}
    for a,bs in edges.items():
        for b in bs:reverse[b].add(a)
    links={a:sorted(set(bs)|reverse[a]) for a,bs in edges.items()}
    save(OUT/'explicit_reference_graph.json',links)
    tokens=lambda t:re.findall(r'[a-z0-9]+',t.lower());cache={}
    for case in cases:
        path=OUT/'runs'/f'{case["id"]}.json'
        if path.exists():continue
        if routes[case['id']] != 'NICE':
            previous=ROOT/'output/research/rag_development/faceted/runs'/path.name
            saved=json.loads(previous.read_text())
            old_source=json.loads((ROOT/'output/research/rag_development/medcpt/corpus.json').read_text())['chunks']
            old_rows=[c for c in old_source if c['guideline_id']==routes[case['id']]]
            new_rows=[c for c in all_chunks if c['guideline_id']==routes[case['id']]]
            if old_rows!=new_rows:raise ValueError('Unchanged-source replay payload differs')
            save(path,{**saved,'replayed_unchanged_source':True,'parent_record_sha256':sha(previous)})
            continue
        src=routes[case['id']];query=focus_query(case['query'])
        eligible=[i for i,c in enumerate(chunks) if c['guideline_id']==src and applicable(c['scope'],case['patient'])]
        bad=[g for g in case['gold_chunk_ids'] if byid[g] not in eligible]
        if bad:raise ValueError('Scope/gold conflict; no label changed: '+case['id'])
        plan=json.loads((OUT/'plans'/f'{plan_key(src,query)}.json').read_text())
        facets=list(dict.fromkeys(plan['questions']))
        key=(src,query,tuple(eligible),tuple(facets))
        if key not in cache:
            bm=BM25Okapi([tokens(texts[i]) for i in eligible])
            qs=list(dict.fromkeys([query,*facets]));mq=medical.query_vectors(qs)
            gq=generic.encode(qs,normalize_embeddings=True,show_progress_bar=False)
            allranks={};pools={};scores={}
            for model,docvectors,queries,reranker in [('medical',mv,mq,medical),('generic',gv,gq,ce)]:
                ranks=[];queries_pools=[]
                for qi,q in enumerate(qs):
                    lexical=bm.get_scores(tokens(q));expanded=bm.get_scores(tokens(expand_query(q)))
                    lexrank=[eligible[j] for j in np.argsort(-lexical,kind='stable') if lexical[j]>0]
                    exprank=[eligible[j] for j in np.argsort(-expanded,kind='stable') if expanded[j]>0]
                    similarity=docvectors@queries[qi]
                    dense=np.array([similarity[owners==i].max() for i in eligible])
                    dense_rank=[eligible[j] for j in np.argsort(-dense,kind='stable')]
                    pool=fuse_rankings([lexrank[:60],exprank[:60],dense_rank[:60]],60)[:60]
                    queries_pools.append(pool);ranks.append((lexrank,dense_rank))
                union=sorted(set(i for pool in queries_pools for i in pool))
                extra={byid[b] for i in union for b in links[chunks[i]['chunk_id']] if byid[b] in eligible}
                graph_pool=sorted(set(union)|extra)
                final_ranks=[];ce_ranks=[]
                for qi,q in enumerate(qs):
                    label=hashlib.sha256(json.dumps([model,src,q,graph_pool,config['corpus_sha256']]).encode()).hexdigest()
                    stored=OUT/'score_cache'/f'{label}.json'
                    if stored.exists():values=json.loads(stored.read_text())['scores']
                    else:
                        values=rerank_scores(q,[texts[i] for i in graph_pool],reranker)
                        save(stored,{'query':q,'model':model,'indices':graph_pool,'scores':values})
                    ordered=[i for i,_ in sorted(zip(graph_pool,values),key=lambda p:(-p[1],p[0]))]
                    ce_ranks.append(ordered)
                    lex,dense=ranks[qi]
                    final_ranks.append(fuse_rankings([lex,dense,[i for i in ordered if i in queries_pools[qi]]],60))
                allranks[model]=(final_ranks,ce_ranks,ranks,queries_pools,graph_pool)
            variants={}
            for model,vec in [('generic',gm),('medical',mm)]:
                final,ceranks,component,qp,gpool=allranks[model]
                facet_indices=[qs.index(q) for q in facets]
                anchors=list(dict.fromkeys(ceranks[i][0] for i in facet_indices if ceranks[i]))
                fused=fuse_rankings([final[i] for i in facet_indices]+[final[0]],60)
                for depth in config['depths']:
                    variants.setdefault(model+'_single',{})[str(depth)]=select_facets(final[0],vec,depth)
                    variants.setdefault(model+'_faceted',{})[str(depth)]=select_facets(fused,vec,depth,anchors)
                    if model=='medical':
                        graph_rank=fuse_rankings([component[i][0] for i in facet_indices]+[component[i][1] for i in facet_indices]+[ceranks[i] for i in facet_indices],60)
                        variants.setdefault('medical_faceted_graph',{})[str(depth)]=select_facets(graph_rank,vec,depth,anchors)
            cache[key]={'rankings':{m:{k:[chunks[i]['chunk_id'] for i in ids] for k,ids in ds.items()} for m,ds in variants.items()},
                        'questions':facets,'plan_available':plan['available'],'eligible_guidance':len(eligible)}
        save(path,{'id':case['id'],'family':case['family'],'guideline':src,'stage':'development_only',**cache[key]})
        print('faceted development',case['id'],flush=True)
    print('Faceted development runs saved; final evaluation remains on hold.',flush=True)


if __name__=='__main__':main()
