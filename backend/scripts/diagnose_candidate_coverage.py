"""Scoring-only candidate-loss audit; never feeds labels into retrieval."""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from rag.evidence_dependency_graph import expand_candidates
from rag.relevance import focus_query
BASE = ROOT / 'output/research'
OUT = BASE / 'rag_development/patient_conditioned'


def main(study='patient_conditioned'):
    out = BASE / 'rag_development' / study
    cases = {c['id']: c for c in json.loads((BASE / 'expanded100/cases.json').read_text())}
    corpus = {c['chunk_id']: c for c in json.loads((BASE / 'rag_development/medcpt/corpus.json').read_text())['chunks']}
    graph = json.loads((out / 'source_dependency_graph.json').read_text()) if study == 'dependencies' else None
    rows, summaries = [], []
    for p in sorted((BASE / 'rag_development/listwise/runs').glob('*.json')):
        r = json.loads(p.read_text())
        c = cases[r['id']]
        candidate_ids = r['candidate_ids']
        if graph is not None:
            candidate_ids, _ = expand_candidates(focus_query(c['query']), candidate_ids, corpus, graph, c['patient'], r['guideline'])
        gold, candidates = set(c['gold_chunk_ids']), set(candidate_ids)
        if not gold <= corpus.keys():
            raise ValueError(f'Missing corpus gold: {r["id"]}')
        missing = sorted(gold - candidates)
        reachable = len(gold & candidates)
        rows.append({'id': r['id'], 'guideline': r['guideline'], 'family': r['family'],
                     'gold_count': len(gold), 'candidate_count': len(candidates),
                     'reachable_gold': reachable, 'missing_gold': '|'.join(missing),
                     'candidate_recall_ceiling_at_4': min(4, reachable) / len(gold),
                     'all_gold_retrievable': not missing})
    for source in ['NICE', 'AAP', 'WHO']:
        selected = [r for r in rows if r['guideline'] == source]
        summaries.append({'guideline': source, 'completed': len(selected), 'total': len(selected),
                          'cases_with_missing_gold': sum(not r['all_gold_retrievable'] for r in selected),
                          'gold_occurrences_missing': sum(r['gold_count'] - r['reachable_gold'] for r in selected),
                          'mean_candidate_recall_ceiling_at_4': sum(r['candidate_recall_ceiling_at_4'] for r in selected) / len(selected)})
    out.mkdir(parents=True, exist_ok=True)
    for name, table in [('candidate_coverage_per_case.csv', rows), ('candidate_coverage_by_source.csv', summaries)]:
        with (out / name).open('w', newline='', encoding='utf8') as f:
            w = csv.DictWriter(f, fieldnames=list(table[0]))
            w.writeheader()
            w.writerows(table)
    (out / 'candidate_coverage_diagnosis.json').write_text(json.dumps({
        'stage': 'scoring_only_development_diagnosis', 'cases': len(rows),
        'summary': summaries,
        'missing_passage_occurrences': dict(Counter(i for r in rows for i in r['missing_gold'].split('|') if i)),
        'interpretation': 'Gold overlap is an engineering relevance annotation, not clinical adjudication. A candidate ceiling describes this retrieval stage, not a natural metric ceiling. It does not justify rescaling scores or changing golds.'
    }, indent=2) + '\n', encoding='utf8')
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', choices=['patient_conditioned', 'dependencies'], default='patient_conditioned')
    main(parser.parse_args().study)
