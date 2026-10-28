"""Bounded query vocabulary for retrieval intent, never patient-fact imputation.

The caller retains the original question. No thresholds, diagnosis, eligibility
or recommendation is inferred. Ambiguous RR/BP abbreviations remain unchanged.
"""
import re

TERMS=[
    (r'\bC[ -]reactive\s+protein\b','C-reactive protein'),
    (r'\bABx\b','antibiotics'),(r'\bBCx\b','blood culture'),
    (r'\bpredisposing features?\b','risk factor'),
    (r'\bpredisposition to infection\b','infection risk'),
    (r'\bbedside evaluations?\b','clinical assessment'),
    (r'\bbedside findings\b','clinical examination findings'),
    (r'\b(?:recorded )?maternal background\b','maternal history'),
    (r'\bPCT\b','procalcitonin laboratory marker'),
    (r'\bWBC\b','white blood cell count laboratory test'),
]


def canonical_query(query):
    if not isinstance(query,str) or not query.strip():raise ValueError('A clinical information question is required')
    text=re.sub(r'[\u2010-\u2015]','-',query)
    for pattern,replacement in TERMS:text=re.sub(pattern,replacement,text,flags=re.I)
    return text
