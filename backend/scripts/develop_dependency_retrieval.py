"""Balanced source-dependency candidate pilot; frozen prior prompts and labels."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from config import get_settings
from rag.evidence_dependency_graph import build_graph, expand_candidates
from rag.guidance_lanes import guidance_role
from rag.patient_passage_ranker import select_patient_passages
from rag.rank_fusion import fuse_rankings
from rag.relevance import focus_query
from scripts.evaluate_expanded import Tracer
from scripts.evaluate_rag_improvements import save
from scripts.evaluation_transport import provider_failure
from services.groq_client import GenerationUnavailable

OUT = ROOT / 'output/research/rag_development/dependencies'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base = ROOT / 'output/research'
    source = base / 'rag_development/medcpt/corpus.json'
    chunks = json.loads(source.read_text())['chunks']
    corpus = {c['chunk_id']: c for c in chunks}
    graph = build_graph([c for c in chunks if guidance_role(c)])
    save(OUT / 'source_dependency_graph.json', graph)
    prior = base / 'rag_development/patient_conditioned'
    ids = json.loads((prior / 'development_protocol.json').read_text())['pilot_case_ids']
    # Labels and reference answers never reach the candidate builder or model.
    cases = {c['id']: {k: c[k] for k in ['id', 'query', 'patient', 'history']}
             for c in json.loads((base / 'expanded100/cases.json').read_text())}
    protocol = {'stage': 'development_only', 'final_evaluation': False, 'pilot_case_ids': ids,
                'model': 'openai/gpt-oss-120b', 'temperature': 0, 'sampling_seed': None,
                'rrf_k': 60, 'candidate_budget': 24, 'dependency_candidate_budget': 4,
                'selected_budget': 8, 'corpus_sha256': sha(source),
                'graph_sha256': sha(OUT / 'source_dependency_graph.json'),
                'code_sha256': {p: sha(ROOT / p) for p in ['backend/rag/evidence_dependency_graph.py',
                    'backend/rag/patient_passage_ranker.py', 'backend/rag/listwise_rerank.py',
                    'backend/scripts/develop_dependency_retrieval.py']},
                'comparison': 'Same 18 cases and patient-conditioned prompt. Candidate expansion only. Unchanged golds. New graph edges are source-text retrieval hints, pending clinical review.'}
    p = OUT / 'development_protocol.json'
    if p.exists() and json.loads(p.read_text()) != protocol:
        raise ValueError('Dependency pilot protocol drift')
    save(p, protocol)
    settings = get_settings().model_copy(update={'llm_provider': 'groq', 'groq_model': protocol['model']})
    for case_id in ids:
        target = OUT / 'runs' / f'{case_id}.json'
        if target.exists():
            continue
        c = cases[case_id]
        previous = json.loads((prior / 'runs' / f'{case_id}.json').read_text())
        question = focus_query(c['query'])
        candidates, added = expand_candidates(question, previous['candidate_ids'], corpus, graph, c['patient'], previous['guideline'])
        record = {k: previous[k] for k in ['id', 'guideline', 'family']}
        record.update(stage='development_only', candidate_ids=candidates, dependency_additions=added)
        if candidates == previous['candidate_ids']:
            record.update(available=previous['available'], selected_ids=previous['selected_ids'],
                          consensus_ids=previous['consensus_ids'], calls=[], exact_request_replay=True)
        else:
            key = hashlib.sha256(json.dumps([question, c['patient'], c['history'], candidates]).encode()).hexdigest()
            trace = Tracer(OUT / 'role_cache' / key, protocol['model'], gap=3)
            try:
                selected = select_patient_passages(question, [corpus[i] for i in candidates], c['patient'], c['history'], settings, llm=trace)
                record.update(available=True, selected_ids=selected, consensus_ids=fuse_rankings([candidates, selected], 60)[:8])
            except GenerationUnavailable as exc:
                if provider_failure(exc.code):
                    save(OUT / 'pending_transport.json', {'id': case_id, 'code': exc.code,
                         'messages': [x.get('provider_message') for x in trace.calls if x.get('provider_message')],
                         'completed': len(list((OUT / 'runs').glob('*.json'))), 'planned_pilot': 18,
                         'policy': 'Provider blocks remain pending, not quality zeros.'})
                    raise SystemExit(75)
                record.update(available=False, selected_ids=[], consensus_ids=candidates[:8], completed_model_error=exc.code)
            except (TypeError, ValueError) as exc:
                record.update(available=False, selected_ids=[], consensus_ids=candidates[:8], completed_contract_error=type(exc).__name__)
            record['calls'] = trace.calls
        save(target, record)
        print('Dependency development', case_id, 'added', len(added), 'valid', record['available'], flush=True)


if __name__ == '__main__':
    main()
