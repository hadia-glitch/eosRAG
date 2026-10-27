"""Clinician-labelled retrieval evaluation; no bundled invented gold answers.

JSONL input: {"query":..., "guideline":"NICE", "relevant_chunk_ids":[...]}
Every gold ID must refer to the reviewed registry and exact corpus revision.
"""
import argparse
import json
from pathlib import Path
from statistics import mean

from config import get_settings
from rag.production_retrieval import retrieve


def evaluate(rows, search):
    scores = []
    for row in rows:
        relevant = set(row['relevant_chunk_ids'])
        if not relevant:
            raise ValueError('Gold relevance labels cannot be empty')
        result = search(row['query'], row['guideline'])
        ids = [c.chunk_id for c in result.chunks]
        hits = relevant.intersection(ids)
        rank = next((i for i, cid in enumerate(ids, 1) if cid in relevant), None)
        scores.append({'recall_at_k': len(hits)/len(relevant), 'reciprocal_rank': 1/rank if rank else 0,
                       'precision_at_k': len(hits)/len(ids) if ids else 0, 'retrieval_mode': result.mode,
                       'corpus_version': result.corpus_version})
    if not scores:
        raise ValueError('No labelled vignettes')
    return {'questions': len(scores), 'mean_recall_at_k': mean(s['recall_at_k'] for s in scores),
            'mrr': mean(s['reciprocal_rank'] for s in scores), 'mean_precision_at_k': mean(s['precision_at_k'] for s in scores),
            'per_question': scores, 'clinical_validity': 'Not measured by retrieval metrics'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--vignettes', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    s = get_settings()
    rows = [json.loads(line) for line in a.vignettes.read_text(encoding='utf-8').splitlines() if line.strip()]
    result = evaluate(rows, lambda q, g: retrieve(q, g, 8, s))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print({k:v for k,v in result.items() if k!='per_question'})
