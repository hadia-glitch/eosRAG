"""Relevance-preserving rank fusion and bounded diversity.

Cross-encoder scores are not calibrated probabilities. A cross-encoder rank
joins lexical and dense ranks rather than replacing both. MMR operates only
inside the relevance head, using bounded ordinal utility, not sigmoid logits
that can collapse to approximately zero and let diversity dominate.
"""
import numpy as np


def fuse_rankings(rankings, k=60):
    scores={}
    for ranking in rankings:
        seen=set()
        for position, key in enumerate(ranking,1):
            if key in seen:continue
            seen.add(key);scores[key]=scores.get(key,0.)+1/(k+position)
    return sorted(scores,key=lambda key:(-scores[key],str(key)))


def guarded_mmr(order, vectors, limit, diversity=.1):
    if not 0 <= diversity <= .2:raise ValueError('Diversity must remain bounded')
    pool=list(order[:max(limit,2*limit)])
    if not pool:return []
    matrix=np.asarray(vectors,dtype=float)[pool]
    if not np.isfinite(matrix).all():raise ValueError('Nonfinite embeddings')
    norms=np.linalg.norm(matrix,axis=1)
    if np.any(norms<=1e-12):raise ValueError('Missing candidate embedding')
    matrix=matrix/norms[:,None]
    sim=matrix@matrix.T
    relevance=np.linspace(1.,0.,len(pool)) if len(pool)>1 else np.ones(1)
    selected=[];remaining=list(range(len(pool)))
    while remaining and len(selected)<limit:
        def utility(i):
            penalty=max([0.,*[sim[i,j] for j in selected]])
            return (1-diversity)*relevance[i]-diversity*penalty
        choice=max(remaining,key=lambda i:(utility(i),-i))
        selected.append(choice);remaining.remove(choice)
    return [pool[i] for i in selected]
