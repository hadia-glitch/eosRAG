"""Versioned evidence-ID pilot, with optional later development expansion."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from config import get_settings
from rag.evidence_dependency_graph import expand_candidates
from rag.evidence_set_ids import select_evidence_ids
from rag.rank_fusion import fuse_rankings
from rag.relevance import focus_query
from scripts.evaluate_expanded import Tracer
from scripts.evaluate_rag_improvements import save
from scripts.evaluation_transport import provider_failure
from services.groq_client import GenerationUnavailable

OUT = ROOT / 'output/research/rag_development/evidence_ids'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(limit):
    base = ROOT / 'output/research'
    source = base / 'rag_development/medcpt/corpus.json'
    corpus = {c['chunk_id']: c for c in json.loads(source.read_text())['chunks']}
    prior = base / 'rag_development/dependencies'
    pilot_ids = json.loads((prior / 'development_protocol.json').read_text())['pilot_case_ids']
    cases = {c['id']: {k: c[k] for k in ['id', 'family', 'query', 'patient', 'history']}
             for c in json.loads((base / 'expanded100/cases.json').read_text())}
    graph_file = prior / 'source_dependency_graph.json'
    graph = json.loads(graph_file.read_text())
    protocol = {'stage': 'development_only', 'final_evaluation': False, 'pilot_case_ids': pilot_ids,
                'total_existing_cases': 100, 'model': 'openai/gpt-oss-120b', 'temperature': 0,
                'sampling_seed': None, 'rrf_k': 60, 'candidate_budget': 24, 'selected_budget': 8,
                'completion_tokens': 4000, 'corpus_sha256': sha(source),
                'dependency_graph_sha256': sha(graph_file),
                'upstream_protocol_sha256': sha(base / 'rag_development/listwise/development_protocol.json'),
                'code_sha256': {p: sha(ROOT / p) for p in ['backend/rag/evidence_set_ids.py',
                    'backend/rag/evidence_dependency_graph.py', 'backend/scripts/develop_evidence_id_retrieval.py']},
                'change': 'Essential/supporting relevance rationale; complete source text is materialized by immutable ID, never generated. Same dependency candidate construction. No labels or engineering answers in prompts.',
                'expansion': 'Review balanced 18-case pilot before explicitly continuing the remaining exposed development cases.',
                'clinical_review_status': 'pending; source identity is not an independent semantic audit'}
    p = OUT / 'development_protocol.json'
    if p.exists() and json.loads(p.read_text()) != protocol:
        raise ValueError('Evidence-ID protocol drift')
    save(p, protocol)
    settings = get_settings().model_copy(update={'llm_provider': 'groq', 'groq_model': protocol['model']})
    ordered_ids = pilot_ids + [i for i in cases if i not in pilot_ids]
    for case_id in ordered_ids[:limit]:
        target = OUT / 'runs' / f'{case_id}.json'
        if target.exists():
            continue
        c = cases[case_id]
        upstream = json.loads((base / 'rag_development/listwise/runs' / f'{case_id}.json').read_text())
        question = focus_query(c['query'])
        candidates, additions = expand_candidates(question, upstream['candidate_ids'], corpus, graph, c['patient'], upstream['guideline'])
        if case_id in pilot_ids:
            old = json.loads((prior / 'runs' / f'{case_id}.json').read_text())
            if candidates != old['candidate_ids']:
                raise ValueError('Pilot candidate construction drift')
        key = hashlib.sha256(json.dumps([question, c['patient'], c['history'], candidates]).encode()).hexdigest()
        trace = Tracer(OUT / 'role_cache' / key, protocol['model'], gap=3)
        record = {'id': case_id, 'guideline': upstream['guideline'], 'family': c['family'],
                  'stage': 'development_only', 'candidate_ids': candidates, 'dependency_additions': additions,
                  'pilot': case_id in pilot_ids}
        try:
            selected, materialized = select_evidence_ids(question, [corpus[i] for i in candidates], c['patient'], c['history'], settings, llm=trace)
            record.update(available=True, selected_ids=selected, selection_rationale=materialized,
                          consensus_ids=fuse_rankings([candidates, selected], 60)[:8])
        except GenerationUnavailable as exc:
            if provider_failure(exc.code):
                save(OUT / 'pending_transport.json', {'id': case_id, 'code': exc.code,
                     'messages': [x.get('provider_message') for x in trace.calls if x.get('provider_message')],
                     'completed': len(list((OUT / 'runs').glob('*.json'))), 'planned_pilot': 18,
                     'policy': 'Provider blocks remain pending, not quality zeros.'})
                raise SystemExit(75)
            record.update(available=False, selected_ids=[], consensus_ids=candidates[:8], completed_model_error=exc.code)
        except (TypeError, ValueError) as exc:
            record.update(available=False, selected_ids=[], consensus_ids=candidates[:8],
                          completed_contract_error=type(exc).__name__, error_reason=str(exc))
        record['calls'] = trace.calls
        save(target, record)
        print('Evidence-ID development', case_id, 'valid', record['available'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, choices=[18, 100], default=18)
    main(parser.parse_args().limit)
