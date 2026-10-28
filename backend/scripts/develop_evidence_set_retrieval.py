"""Inspectable evidence-set development pilot; no final evaluation or deployment."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from config import get_settings
from rag.evidence_set_ranker import select_evidence_set
from rag.rank_fusion import fuse_rankings
from rag.relevance import focus_query
from scripts.evaluate_expanded import Tracer
from scripts.evaluate_rag_improvements import save
from scripts.evaluation_transport import provider_failure
from services.groq_client import GenerationUnavailable

OUT = ROOT / 'output/research/rag_development/evidence_sets'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base = ROOT / 'output/research'
    source = base / 'rag_development/medcpt/corpus.json'
    corpus = {c['chunk_id']: c for c in json.loads(source.read_text())['chunks']}
    prior = base / 'rag_development/dependencies'
    ids = json.loads((prior / 'development_protocol.json').read_text())['pilot_case_ids']
    cases = {c['id']: {k: c[k] for k in ['id', 'query', 'patient', 'history']}
             for c in json.loads((base / 'expanded100/cases.json').read_text())}
    protocol = {'stage': 'development_only', 'final_evaluation': False, 'pilot_case_ids': ids,
                'model': 'openai/gpt-oss-120b', 'temperature': 0, 'sampling_seed': None,
                'rrf_k': 60, 'candidate_budget': 24, 'selected_budget': 8,
                'completion_tokens': 4000, 'corpus_sha256': sha(source),
                'upstream_protocol_sha256': sha(prior / 'development_protocol.json'),
                'code_sha256': {p: sha(ROOT / p) for p in ['backend/rag/evidence_set_ranker.py',
                    'backend/scripts/develop_evidence_set_retrieval.py']},
                'change': 'Explicit essential/supporting relevance rationale and exact source quote per choice. Same dependency candidate pools. No golds or reference answers in prompts.',
                'clinical_review_status': 'pending; quoted selection is not an independent semantic audit'}
    p = OUT / 'development_protocol.json'
    if p.exists() and json.loads(p.read_text()) != protocol:
        raise ValueError('Evidence-set protocol drift')
    save(p, protocol)
    settings = get_settings().model_copy(update={'llm_provider': 'groq', 'groq_model': protocol['model']})
    for case_id in ids:
        target = OUT / 'runs' / f'{case_id}.json'
        if target.exists():
            continue
        c = cases[case_id]
        previous = json.loads((prior / 'runs' / f'{case_id}.json').read_text())
        question = focus_query(c['query'])
        candidates = previous['candidate_ids']
        key = hashlib.sha256(json.dumps([question, c['patient'], c['history'], candidates]).encode()).hexdigest()
        trace = Tracer(OUT / 'role_cache' / key, protocol['model'], gap=3)
        record = {k: previous[k] for k in ['id', 'guideline', 'family']}
        record.update(stage='development_only', candidate_ids=candidates)
        try:
            selected, rationale = select_evidence_set(question, [corpus[i] for i in candidates], c['patient'], c['history'], settings, llm=trace)
            record.update(available=True, selected_ids=selected, selection_rationale=rationale,
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
        print('Evidence-set development', case_id, 'valid', record['available'], flush=True)


if __name__ == '__main__':
    main()
