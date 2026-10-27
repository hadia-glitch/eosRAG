"""Clinical-intent coverage with bounded, observable MMR diversity."""
import numpy as np


def select_facets(order,vectors,limit,anchors=(),diversity=.15):
    if not 0<=diversity<=.2 or limit<1:raise ValueError('Invalid selection budget')
    pool=list(dict.fromkeys([*anchors,*order[:2*limit]]))
    if not pool:return []
    x=np.asarray(vectors,dtype=float)
    norms=np.linalg.norm(x,axis=1)
    if not np.isfinite(x).all() or any(norms[i]<=1e-12 for i in pool):raise ValueError('Invalid candidate vectors')
    x=x/(norms[:,None]+1e-12)
    rank={i:r for r,i in enumerate(order)}
    denominator=max(1,len(order[:2*limit])-1)
    relevance={i:max(0.,1-rank.get(i,denominator)/denominator) for i in pool}
    chosen=list(dict.fromkeys(anchors))[:limit]
    while len(chosen)<limit:
        remaining=[i for i in pool if i not in chosen]
        if not remaining:break
        def utility(i):
            redundancy=max([0.,*[float(x[i]@x[j]) for j in chosen]])
            return (1-diversity)*relevance[i]-diversity*redundancy
        chosen.append(max(remaining,key=lambda i:(utility(i),-rank.get(i,denominator))))
    return chosen
