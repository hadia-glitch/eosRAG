"""Bounded terminology expansion and MMR selection, not clinical decision rules."""
import re
import numpy as np

SYNONYMS = [
    (r'\b(?:eos|early[- ]onset sepsis)\b','early onset neonatal infection'),
    (r'\b(?:apnea|apnoea)\b','apnoea apnea'),
    (r'\b(?:hypoxia|hypoxemia|hypoxaemia|spo2)\b','hypoxia reduced oxygen saturation'),
    (r'\b(?:tachypnea|tachypnoea|breathing difficulties)\b','respiratory distress tachypnoea'),
    (r'\b(?:crp|c[- ]reactive protein)\b','C-reactive protein CRP'),
    (r'\b(?:gbs|group b strep)\b','group B streptococcus'),
    (r'\b(?:stop|stopping|discontinue|discontinuation)\b','stop antibiotics treatment duration'),
    (r'\b(?:blood culture|culture negative|negative culture)\b','blood culture microbiological investigations'),
]


def expand_query(query):
    normalized=re.sub(r'[\u2010-\u2015]','-',query)
    extras=[]
    for pattern,expansion in SYNONYMS:
        if re.search(pattern,normalized,re.I):extras.append(expansion)
    return (query+' '+' '.join(dict.fromkeys(extras)))[:2500].strip()


def mmr_indices(scores,embeddings,limit,diversity=.2):
    x=np.asarray(embeddings,dtype=float);s=np.asarray(scores,dtype=float)
    if x.ndim!=2 or len(x)!=len(s) or not np.isfinite(x).all() or not np.isfinite(s).all():raise ValueError('Invalid MMR inputs')
    norms=np.linalg.norm(x,axis=1)
    if (norms<=1e-12).any():raise ValueError('Empty MMR embeddings')
    x=x/norms[:,None]
    similarity=x@x.T
    # Bounded cross-encoder ranking utility, not calibrated clinical confidence.
    # Unlike shortlist min/max, this does not magnify tiny logit differences.
    relevant=1/(1+np.exp(-np.clip(s,-60,60)))
    selected=[];remaining=list(range(len(s)))
    while remaining and len(selected)<limit:
        def utility(i):
            redundancy=max(similarity[i,j] for j in selected) if selected else 0
            return (1-diversity)*relevant[i]-diversity*redundancy
        chosen=max(remaining,key=lambda i:(utility(i),s[i],-i))
        selected.append(chosen);remaining.remove(chosen)
    return selected
