"""Score saved patient-conditioned development without changing the frozen pilot."""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from scripts.summarize_faceted_development import scores
from scripts.summarize_expanded import ci
from scripts.evaluate_rag_improvements import save

OUT = ROOT / 'output/research/rag_development/patient_conditioned'
METRICS = ['recall', 'precision', 'mrr', 'ndcg', 'f1', 'precision_ceiling']


def write(name, rows):
    if rows:
        with (OUT / name).open('w', newline='', encoding='utf8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def main(study='patient_conditioned'):
    global OUT
    OUT = ROOT / 'output/research/rag_development' / study
    base = ROOT / 'output/research'
    cases = {c['id']: c for c in json.loads((base / 'expanded100/cases.json').read_text())}
    corpus = {c['chunk_id']: c for c in json.loads((base / 'rag_development/medcpt/corpus.json').read_text())['chunks']}
    protocol = json.loads((OUT / 'development_protocol.json').read_text())
    records = {p.stem: json.loads(p.read_text()) for p in (OUT / 'runs').glob('*.json')}
    missing = [i for i in protocol['pilot_case_ids'] if i not in records]
    if missing:
        raise SystemExit(f'Balanced pilot incomplete: {len(missing)} pending; no quality zeros or complete summary emitted')
    planned = protocol.get('total_existing_cases', len(protocol['pilot_case_ids']))
    rows, summary, paired, validity = [], [], [], []
    populations = [('balanced_pilot', protocol['pilot_case_ids'])]
    if len(records) == 100:
        populations.append(('complete_development', list(cases)))
    for population, ids in populations:
        methods = ['patient_selected', 'patient_consensus', 'question_consensus']
        include_prior = study in {'dependencies', 'evidence_ids'} and population == 'balanced_pilot'
        if include_prior:
            methods.append('prior_patient_consensus')
        if study == 'evidence_ids' and population == 'balanced_pilot':
            methods.append('dependency_consensus')
        for case_id in ids:
            r = records[case_id]
            old = json.loads((base / 'rag_development/consensus/runs' / f'{case_id}.json').read_text())
            if not set(cases[case_id]['gold_chunk_ids']) <= corpus.keys():
                raise ValueError(f'Missing gold passage: {case_id}')
            for k in [4, 8]:
                rankings = [('patient_selected', r['selected_ids'][:k]),
                            ('patient_consensus', r['consensus_ids'][:k]),
                            ('question_consensus', old['rankings'][str(k)])]
                if include_prior:
                    prior = json.loads((base / 'rag_development/patient_conditioned/runs' / f'{case_id}.json').read_text())
                    rankings.append(('prior_patient_consensus', prior['consensus_ids'][:k]))
                if study == 'evidence_ids' and population == 'balanced_pilot':
                    prior = json.loads((base / 'rag_development/dependencies/runs' / f'{case_id}.json').read_text())
                    rankings.append(('dependency_consensus', prior['consensus_ids'][:k]))
                for method, ranked in rankings:
                    if not set(ranked) <= corpus.keys():
                        raise ValueError(f'Unknown retrieved ID: {case_id}')
                    rows.append({'population': population, 'id': case_id, 'guideline': r['guideline'],
                                 'family': r['family'], 'method': method, 'depth': k,
                                 'selector_valid': r['available'],
                                 **scores(ranked, set(cases[case_id]['gold_chunk_ids']), k)})
        for g in ['NICE', 'AAP', 'WHO']:
            source_records = [records[i] for i in ids if records[i]['guideline'] == g]
            validity.append({'population': population, 'guideline': g, 'completed': len(source_records),
                             'total': len(source_records), 'selector_valid': sum(r['available'] for r in source_records),
                             'empty_selections': sum(r['available'] and not r['selected_ids'] for r in source_records),
                             'interpretation': 'Structural selection validity, not clinical usability or care-plan release coverage'})
            for method in methods:
                for k in [4, 8]:
                    selected = [r for r in rows if (r['population'], r['guideline'], r['method'], r['depth']) == (population, g, method, k)]
                    for metric in METRICS:
                        summary.append({'population': population, 'guideline': g, 'method': method,
                                        'depth': k, 'metric': metric, 'completed': len(selected),
                                        'total': len(selected),
                                        **ci([r[metric] for r in selected], [r['family'] for r in selected])})
            for baseline in [m for m in methods if m.endswith('consensus') and not m.startswith('patient_')]:
                for method in ['patient_selected', 'patient_consensus']:
                    for k in [4, 8]:
                        left = [r for r in rows if (r['population'], r['guideline'], r['method'], r['depth']) == (population, g, method, k)]
                        right = {r['id']: r for r in rows if (r['population'], r['guideline'], r['method'], r['depth']) == (population, g, baseline, k)}
                        for metric in METRICS:
                            paired.append({'population': population, 'guideline': g,
                                           'contrast': method + ' minus ' + baseline, 'depth': k,
                                           'metric': metric, 'paired_n': len(left),
                                           **ci([r[metric] - right[r['id']][metric] for r in left], [r['family'] for r in left])})
    write('per_case.csv', rows)
    write('intervals.csv', summary)
    write('paired_differences.csv', paired)
    write('selector_validity.csv', validity)
    save(OUT / 'summary.json', {'stage': 'development_only', 'final_evaluation': False,
         'completed_existing_cases': len(records), 'planned_existing_cases': planned,
         'balanced_pilot_complete': True, 'complete_development': len(records) == 100,
         'statistics': summary, 'paired': paired, 'selector_validity': validity,
         'limitations': 'Previously examined synthetic cases; engineering golds, no clinician adjudication. Retrieval validity is not clinical usability. Provider failures remain pending, not quality zeros.'})
    lines = ['# Patient-conditioned retrieval development', '',
             f'Study: {study}. Saved cases: {len(records)}/{planned}. Balanced pilot: 18/18. Final evaluation remains on hold.', '',
             '|Population|Source|Method|N|Recall@4|MRR@4|Recall@8|', '|---|---|---|---:|---:|---:|---:|']
    for population, ids in populations:
        methods = ['patient_selected', 'patient_consensus', 'question_consensus']
        if study in {'dependencies', 'evidence_ids'} and population == 'balanced_pilot':
            methods.append('prior_patient_consensus')
        if study == 'evidence_ids' and population == 'balanced_pilot':
            methods.append('dependency_consensus')
        for g in ['NICE', 'AAP', 'WHO']:
            for method in methods:
                def value(metric, k):
                    return next(r['mean'] for r in summary if (r['population'], r['guideline'], r['method'], r['depth'], r['metric']) == (population, g, method, k, metric))
                n = sum(records[i]['guideline'] == g for i in ids)
                lines.append(f'|{population}|{g}|{method}|{n}|{value("recall",4):.6f}|{value("mrr",4):.6f}|{value("recall",8):.6f}|')
    lines += ['', 'Intervals and paired differences retain 2,000 case and whole-family bootstrap resamples (seed 31). The six-case source pilot has one example per family; its intervals cannot establish broad generalization. Gold IDs and patient data remain unchanged.']
    (OUT / 'results.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    print('\n'.join(lines))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', choices=['patient_conditioned', 'dependencies', 'evidence_ids'], default='patient_conditioned')
    main(parser.parse_args().study)
