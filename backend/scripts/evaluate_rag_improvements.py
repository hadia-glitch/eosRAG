"""Versioned, resumable improvement study; never overwrites expanded100.

The previously examined 100 cases are a development/regression benchmark, NOT
an independent test set. All declared variants and negative results are saved.
No gold IDs, reference answers or family labels reach the retrieval function.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
OUT = ROOT / 'output/research/rag_improvement_v1'
OLD = ROOT / 'output/research/expanded100'


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(ids, gold, k=4):
    hits = [int(x in gold) for x in ids[:k]]
    n = len(gold)
    dcg = sum(h / np.log2(i + 2) for i, h in enumerate(hits))
    ideal = sum(1 / np.log2(i + 2) for i in range(min(n, k)))
    return {'recall_at_4': sum(hits) / n, 'precision_at_4': sum(hits) / k,
            'mrr_at_4': next((1 / (i + 1) for i, h in enumerate(hits) if h), 0),
            'ndcg_at_4': float(dcg / ideal), 'hit_at_4': int(any(hits)),
            'precision_at_4_ceiling': min(n, k) / k, 'recall_at_4_ceiling': min(n, k) / n}


def freeze():
    config = {'seed': 31, 'rrf_k': 60, 'k': 4, 'candidate_limit': 60,
              'embedding_models': ['sentence-transformers/all-MiniLM-L6-v2', 'intfloat/e5-small-v2'],
              'reranker': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
              'windows': {'words': 180, 'overlap': 40}, 'mmr_diversity': 0.2,
              'variants': ['focused_hybrid', 'expanded_rrf_ce', 'expanded_rrf_ce_mmr', 'decomposed_rrf_ce_mmr'],
              'label_access': 'Scoring only; neither family nor gold nor reference passed to search.',
              'design': 'Post-hoc development/regression comparison on previously examined synthetic cases. No independent generalization claim.',
              'cases_sha256': sha(OLD / 'cases.json'), 'corpus_sha256': sha(OLD / 'corpus.json'),
              'code_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in [Path(__file__).resolve(), ROOT/'backend/rag/relevance.py', ROOT/'backend/rag/selection.py']}}
    path = OUT / 'retrieval_protocol.json'
    if path.exists():
        if json.loads(path.read_text()) != config:
            raise ValueError('Frozen improvement protocol drift: use a new version directory')
    else:
        save(path, config)
    return config


def decompose(query):
    # Syntax-only decomposition. No diagnosis, thresholds or generated guidance.
    parts = re.split(r';\s*|\band\s+(?=explain|review|assess|describe|identify)', query, flags=re.I)
    return list(dict.fromkeys([query, *[p.strip() for p in parts if len(p.split()) >= 5]]))[:4]


def search(query, texts, bm, encoder, vectors, reranker, config, model_name):
    from rag.relevance import focus_query, rerank_scores
    from rag.selection import expand_query, mmr_indices
    query = focus_query(query)
    expanded = expand_query(query)
    e5 = 'e5-' in model_name
    encode = lambda q: encoder.encode(('query: ' if e5 else '') + q, normalize_embeddings=True)
    tokens = lambda q: re.findall(r'[a-z0-9]+', q.lower())
    base_scores = [bm.get_scores(tokens(query)), vectors @ encode(query)]
    def fusion(score_arrays):
        fused = np.zeros(len(texts))
        for scores in score_arrays:
            order = np.argsort(-scores, kind='stable')[:config['candidate_limit']]
            # Zero BM25 scores are not lexical matches.
            order = order[scores[order] > 0] if np.max(scores) > 1 else order
            fused[order] += 1 / (config['rrf_k'] + np.arange(1, len(order) + 1))
        return np.argsort(-fused, kind='stable')[:config['candidate_limit']]
    simple = fusion(base_scores)
    arrays = [*base_scores, bm.get_scores(tokens(expanded))]
    shortlist = fusion(arrays)
    parts = decompose(query)
    decomposed = fusion([*arrays, *[bm.get_scores(tokens(p)) for p in parts[1:]], *[vectors @ encode(p) for p in parts[1:]]])
    union = sorted(set(shortlist) | set(decomposed))
    scores = rerank_scores(query, [texts[i] for i in union], reranker)
    byindex = dict(zip(union, scores))
    def select(indices, mmr):
        indices = sorted(indices, key=lambda i: (-byindex[i], i))
        if mmr:
            chosen = mmr_indices([byindex[i] for i in indices], vectors[indices], 4, diversity=config['mmr_diversity'])
            return [int(indices[i]) for i in chosen]
        return [int(i) for i in indices[:4]]
    return {'focused_hybrid': [int(i) for i in simple[:4]],
            'expanded_rrf_ce': select(shortlist, False), 'expanded_rrf_ce_mmr': select(shortlist, True),
            'decomposed_rrf_ce_mmr': select(decomposed, True)}


def retrieval(model_name):
    import torch
    from rank_bm25 import BM25Okapi
    from sentence_transformers import SentenceTransformer, CrossEncoder
    torch.set_num_threads(4)
    config = freeze()
    if model_name not in config['embedding_models']:
        raise ValueError('Undeclared embedding model')
    encoder = SentenceTransformer(model_name)
    reranker = CrossEncoder(config['reranker'])
    cases = json.loads((OLD/'cases.json').read_text())
    corpus = json.loads((OLD/'corpus.json').read_text())['chunks']
    model_dir = OUT/'retrieval'/model_name.replace('/', '__')
    for guideline in ['NICE', 'AAP', 'WHO']:
        chunks = [c for c in corpus if c['guideline_id'] == guideline]
        texts = [c['text'] for c in chunks]
        prefix = 'passage: ' if 'e5-' in model_name else ''
        vectors = encoder.encode([prefix+t for t in texts], normalize_embeddings=True, show_progress_bar=False)
        bm = BM25Okapi([re.findall(r'[a-z0-9]+', t.lower()) for t in texts])
        for case in cases:
            if not case['gold_chunk_ids'][0].startswith(guideline):
                continue
            path = model_dir / f'{case["id"]}.json'
            if path.exists():
                continue
            # Explicitly pass only the question, not case labels/references.
            ranks = search(case['query'], texts, bm, encoder, vectors, reranker, config, model_name)
            save(path, {'id': case['id'], 'guideline': guideline, 'model': model_name,
                        'rankings': {key: [chunks[i]['chunk_id'] for i in ix] for key, ix in ranks.items()}})
            print(model_name, guideline, case['id'], flush=True)
    save(model_dir/'runtime.json', {'torch': torch.__version__, 'encoder': model_name,
         'encoder_revision': getattr(encoder[0].auto_model.config, '_commit_hash', None),
         'reranker_revision': getattr(reranker.model.config, '_commit_hash', None)})


def summarize():
    import csv
    config = freeze()
    cases = {c['id']: c for c in json.loads((OLD/'cases.json').read_text())}
    rows = []
    for path in sorted((OUT/'retrieval').glob('*/*.json')):
        r = json.loads(path.read_text())
        if 'rankings' not in r:
            continue
        c = cases[r['id']]
        for variant, ids in r['rankings'].items():
            rows.append({'id': r['id'], 'guideline': r['guideline'], 'family': c['family'], 'model': r['model'],
                         'variant': variant, **metrics(ids, set(c['gold_chunk_ids']))})
    old = json.loads((OLD/'retrieval.json').read_text())['cases']
    for r in old:
        c = cases[r['id']]
        for v, ids in r['rankings'].items():
            rows.append({'id': r['id'], 'guideline': c['gold_chunk_ids'][0].split('-')[0].replace('2018','').replace('2024',''),
                         'family': c['family'], 'model': 'historical_MiniLM', 'variant': v,
                         **metrics(ids, set(c['gold_chunk_ids']))})
    def csvsave(name, data):
        with (OUT/name).open('w', newline='', encoding='utf8') as f:
            w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
    csvsave('retrieval_per_case.csv', rows)
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r['guideline'], r['model'], r['variant'])].append(r)
    summaries = []
    for key, group in sorted(groups.items()):
        result = dict(zip(['guideline', 'model', 'variant'], key)); result['n'] = len(group)
        rng = np.random.default_rng(config['seed'])
        samples = rng.integers(0, len(group), size=(2000, len(group)))
        for metric in metrics([], {'x'}):
            values = np.array([r[metric] for r in group])
            lo, hi = np.quantile(values[samples].mean(axis=1), [.025, .975])
            result.update({metric: float(values.mean()), metric+'_ci_low': float(lo), metric+'_ci_high': float(hi)})
        summaries.append(result)
    csvsave('retrieval_summary.csv', summaries)
    save(OUT/'retrieval_summary.json', summaries)
    lines = ['# RAG improvement study', '', 'Post-hoc development results on the previously examined 100 synthetic cases; not an independent clinical test.', '',
             '|Source|Embedding|Variant|N|Recall@4|Precision@4 (ceiling)|MRR@4|nDCG@4|', '|---|---|---|---:|---:|---:|---:|---:|']
    for r in summaries:
        lines.append(f"|{r['guideline']}|{r['model']}|{r['variant']}|{r['n']}|{r['recall_at_4']:.4f}|{r['precision_at_4']:.4f} ({r['precision_at_4_ceiling']:.4f})|{r['mrr_at_4']:.4f}|{r['ndcg_at_4']:.4f}|")
    lines += ['', 'Gold relevance is not exhaustively clinician adjudicated. Additional valid passages may be counted as false positives. Precision ceiling = min(number of labelled relevant passages, 4)/4; recall ceiling = min(number of labelled relevant passages, 4)/number of labelled relevant passages. MRR and normalized DCG have ceiling 1 when a relevant first result exists and ideal ordering is attainable. BLEU/METEOR/ROUGE/BERTScore have no justified 0.8 clinical target: wording overlap is not clinical correctness. Fault rejection must remain high; reducing the number of detected injected faults would be a regression.', '', 'All variants, including negative comparisons, are retained. Case bootstrap intervals use 2,000 resamples, seed 31.']
    (OUT/'results.md').write_text('\n'.join(lines)+'\n', encoding='utf8')
    print('\n'.join(lines), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--model'); parser.add_argument('--summarize', action='store_true')
    args = parser.parse_args()
    if args.model:
        retrieval(args.model)
    if args.summarize:
        summarize()
