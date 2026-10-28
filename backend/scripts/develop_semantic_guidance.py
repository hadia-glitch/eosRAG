"""Development fixes: complete small-source CE coverage, genres, definition graph.

No Groq calls. Golds only validate annotation conflicts and score saved outputs.
Old source corpora, query plans and experiments are preserved.
"""
import hashlib
import json
import re
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from rag.clinical_scope import applicable
from rag.guidance_lanes import guidance_role
from rag.source_retrieval_views import genre,retrieval_view,topic_admission
from rag.relevance import focus_query,passage_windows,rerank_scores
from rag.rank_fusion import fuse_rankings
from rag.faceted_selection import select_facets
from rag.bounded_facets import select_guarded_facets
from scripts.evaluate_rag_improvements import save

BASE=ROOT/'output/research/rag_development'
OUT=BASE/'semantic_guidance'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    import torch
    from sentence_transformers import CrossEncoder
    from rag.medical_models import MedCPT
    torch.set_num_threads(4)
    source=BASE/'recommendation_units/corpus.json'
    corpus=json.loads(source.read_text())['chunks']
    chunks=[c for c in corpus if guidance_role(c)]
    by_id={c['chunk_id']:i for i,c in enumerate(chunks)}
    casefile=ROOT/'output/research/expanded100/cases.json'
    fullcases=json.loads(casefile.read_text())
    cases=[{k:c[k] for k in ['id','family','query','patient']} for c in fullcases]
    golds={c['id']:set(c['gold_chunk_ids']) for c in fullcases}
    graphfile=BASE/'definition_context_graph.json'
    graph=json.loads(graphfile.read_text())
    upstream=BASE/'recommendation_units/guarded_facets'
    protocol={'stage':'development_only','final_evaluation':False,'cases_sha256':sha(casefile),
        'corpus_sha256':sha(source),'definition_graph_sha256':sha(graphfile),
        'parent_protocol_sha256':sha(upstream/'development_protocol.json'),
        'methods':['ce_full_pool','ce_guidance_genre','ce_definition_graph'],
        'depths':[4,8],'rrf_k':60,'mmr_diversity':.15,'new_groq_calls':0,
        'candidate_policy':'All source/age/setting/topic-admitted guidance passages in the small reviewed-structure lane; no preliminary top-60 loss.',
        'fusion':'Equal RRF60 of original-question and existing-facet CE rankings for both frozen cross encoders. Lexical/dense ranks do not override CE relevance.',
        'graph':'Exact publisher definitions enrich scoring text only. Original passages stay immutable. Additional released definition context is counted separately.',
        'clinical_review_status':'pending; engineering scope/genre extraction is not clinical approval',
        'code_sha256':{p:sha(ROOT/p) for p in ['backend/scripts/develop_semantic_guidance.py','backend/rag/source_retrieval_views.py','backend/rag/relevance.py','backend/rag/faceted_selection.py','backend/rag/bounded_facets.py']}}
    target=OUT/'development_protocol.json'
    if target.exists() and json.loads(target.read_text())!=protocol:raise ValueError('Semantic-guidance development protocol drift')
    save(target,protocol)
    medical=MedCPT();generic=CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    save(OUT/'model_revisions.json',{**medical.revisions,'cross-encoder/ms-marco-MiniLM-L-6-v2':getattr(generic.model.config,'_commit_hash',None)})
    owners=[]
    for i,c in enumerate(chunks):
        owners.extend([i]*len(passage_windows(c['raw_text'])))
    owners=np.array(owners)
    with np.load(BASE/'recommendation_units/faceted/embedding_cache/documents.npz') as arrays:
        vectors=np.array([arrays['medical'][owners==i].mean(axis=0) for i in range(len(chunks))])
    # Exact cached cells are reused only from their matching corpus/source.
    cells={};inherited=0;conflicts=[]
    for folder,allowed in [(BASE/'faceted/score_cache',{'AAP','WHO'}),(BASE/'recommendation_units/faceted/score_cache',{'NICE'})]:
        for path in sorted(folder.glob('*.json')):
            r=json.loads(path.read_text());sources={chunks[i]['guideline_id'] for i in r['indices']}
            if len(sources)!=1:raise ValueError('Mixed-source old score cache')
            src=next(iter(sources))
            if src not in allowed:continue
            for i,value in zip(r['indices'],r['scores']):
                key=(r['model'],src,r['query'],chunks[i]['chunk_id'],hashlib.sha256(chunks[i]['text'].encode()).hexdigest())
                if key in cells and abs(cells[key]-value)>1e-3:conflicts.append({'chunk_id':chunks[i]['chunk_id'],'delta':abs(cells[key]-value)})
                if key not in cells:cells[key]=value;inherited+=1
    if conflicts:raise ValueError('Inconsistent frozen cached CE cells; inspect before proceeding')
    new_pairs=0;scope_audit=[]
    def score(model_name,model,src,q,indices,texts):
        nonlocal new_pairs
        hashes=[hashlib.sha256(t.encode()).hexdigest() for t in texts]
        keys=[(model_name,src,q,chunks[i]['chunk_id'],h) for i,h in zip(indices,hashes)]
        label=hashlib.sha256(json.dumps([model_name,src,q,list(zip(indices,hashes))]).encode()).hexdigest()
        path=OUT/'score_cache'/f'{label}.json'
        if path.exists():
            saved=json.loads(path.read_text())
            if saved['query']!=q or saved['indices']!=indices or saved['view_hashes']!=hashes:raise ValueError('CE view cache mismatch')
            for key,value in zip(keys,saved['scores']):cells[key]=value
        missing=[j for j,key in enumerate(keys) if key not in cells]
        if missing:
            values=rerank_scores(q,[texts[j] for j in missing],model)
            for j,value in zip(missing,values):cells[keys[j]]=value
            new_pairs+=len(missing)
        values=[cells[key] for key in keys]
        save(path,{'model':model_name,'query':q,'indices':indices,'view_hashes':hashes,'scores':values})
        return values
    for case in cases:
        path=OUT/'runs'/f'{case["id"]}.json'
        if path.exists():continue
        parent=json.loads((upstream/'runs'/path.name).read_text())
        src=parent['guideline'];q=focus_query(case['query'])
        eligible=[]
        for i,c in enumerate(chunks):
            if c['guideline_id']!=src or not applicable(c['scope'],case['patient']):continue
            allowed,reason=topic_admission(c,q,case['patient'])
            if allowed:eligible.append(i)
            else:scope_audit.append({'id':case['id'],'chunk_id':c['chunk_id'],'reason':reason})
        excluded=golds[case['id']]-{chunks[i]['chunk_id'] for i in eligible}
        if excluded:
            save(OUT/'scope_gold_conflict.json',{'id':case['id'],'excluded':sorted(excluded)})
            raise ValueError('Source/gold scope conflict; no labels changed')
        qs=list(dict.fromkeys([q,*parent['questions']]))
        views={'plain':[chunks[i]['text'] for i in eligible]}
        definition_nodes={}
        enriched=[]
        for i in eligible:
            text,nodes=retrieval_view(chunks[i],graph,case['patient']);enriched.append(text)
            definition_nodes[chunks[i]['chunk_id']]=[n['chunk_id'] for n in nodes]
        views['definitions']=enriched
        ranks={}
        for view,texts in views.items():
            result=[]
            for model_name,model in [('medical',medical),('generic',generic)]:
                for question in qs:
                    values=score(model_name,model,src,question,eligible,texts)
                    result.append([i for i,_ in sorted(zip(eligible,values),key=lambda p:(-p[1],p[0]))])
            ranks[view]=result
        researcher=bool(re.search(r'\b(?:cohort|trial|published studies|study results|meta.analysis|research evidence)\b',q,re.I))
        primary={i for i in eligible if genre(chunks[i])!='study_background' or researcher}
        methods={}
        for name,view,genre_guard in [('ce_full_pool','plain',False),('ce_guidance_genre','plain',True),('ce_definition_graph','definitions',True)]:
            ranked=[[i for i in r if i in primary] if genre_guard else r for r in ranks[view]]
            order=fuse_rankings(ranked,60)
            # Fallback background remains available when core guidance is scarce.
            order+= [i for i in fuse_rankings(ranks[view],60) if i not in order]
            original=fuse_rankings([ranked[0],ranked[len(qs)]],60)
            anchors=list(dict.fromkeys(r[0] for j,r in enumerate(ranked) if j%len(qs)!=0 and r))
            methods[name]={}
            for depth in [4,8]:
                chosen=select_guarded_facets(order,vectors,depth,anchors,question_order=original) if genre_guard else select_facets(order,vectors,depth)
                methods[name][str(depth)]=[chunks[i]['chunk_id'] for i in chosen]
        save(path,{'id':case['id'],'guideline':src,'family':case['family'],'stage':'development_only',
             'rankings':methods,'eligible_candidates':len(eligible),'questions':qs,'definition_context_ids':definition_nodes,
             'evidence_genres':{chunks[i]['chunk_id']:genre(chunks[i]) for i in eligible},
             'component_original_rankings':{view:{'medical':[chunks[i]['chunk_id'] for i in rs[0]],'generic':[chunks[i]['chunk_id'] for i in rs[len(qs)]]} for view,rs in ranks.items()}})
        save(OUT/'progress.json',{'completed':len(list((OUT/'runs').glob('*.json'))),'planned':100,'inherited_cached_pairs':inherited,'new_scored_pairs_this_invocation':new_pairs,'new_groq_calls':0})
        print('Semantic-guidance development',case['id'],'candidates',len(eligible),'new CE pairs',new_pairs,flush=True)
    save(OUT/'source_topic_audit.json',scope_audit)
    print('Development only: 100 saved cases; no final evaluation or Groq calls.',flush=True)


if __name__=='__main__':main()
