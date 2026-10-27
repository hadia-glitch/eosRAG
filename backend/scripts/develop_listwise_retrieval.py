"""Development-only reranking; labels and reference answers never enter prompts.

Frozen upstream rankings are consumed unchanged. This script emits rankings,
not patient advice, and does not start the held final generation experiment.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from config import get_settings
from rag.rank_fusion import fuse_rankings
from rag.clinical_scope import applicable
from rag.relevance import focus_query
from rag.listwise_rerank import select_passages
from scripts.evaluate_expanded import Tracer
from scripts.evaluate_rag_improvements import save
from scripts.evaluation_transport import provider_failure
from services.groq_client import GenerationUnavailable

OUT = ROOT / 'output/research/rag_development/listwise'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT / 'output/research/rag_development/medcpt/corpus.json'
    upstream = ROOT / 'output/research/rag_development/faceted'
    corpus = {c['chunk_id']: c for c in json.loads(source.read_text())['chunks']}
    # Immediately discard labels and engineering answers from the case input.
    cases = [{k: c[k] for k in ('id', 'family', 'query', 'patient')}
             for c in json.loads((ROOT / 'output/research/expanded100/cases.json').read_text())]
    protocol = {'stage': 'development_only', 'final_evaluation': False,
                'model': 'openai/gpt-oss-120b', 'temperature': 0, 'sampling_seed': None,
                'candidate_budget': 24, 'selected_budget': 8, 'rrf_k': 60,
                'upstream_methods': ['generic_single', 'medical_single', 'generic_faceted', 'medical_faceted'],
                'upstream_depth': 12, 'corpus_sha256': sha(source),
                'upstream_protocol_sha256': sha(upstream / 'development_protocol.json'),
                'code_sha256': {p: sha(ROOT / p) for p in ['backend/rag/listwise_rerank.py',
                    'backend/scripts/develop_listwise_retrieval.py']},
                'prompt_inputs': 'Original focused question, source headings and full eligible candidate texts. No golds or reference answers.',
                'cache': 'Identical focused question and identical ordered candidate identifiers share an exact request.',
                'clinical_validation': 'not established'}
    target = OUT / 'development_protocol.json'
    if target.exists() and json.loads(target.read_text()) != protocol:
        raise ValueError('Frozen listwise development configuration drift')
    save(target, protocol)
    settings = get_settings().model_copy(update={'llm_provider': 'groq', 'groq_model': protocol['model']})
    for case in cases:
        target = OUT / 'runs' / f'{case["id"]}.json'
        if target.exists():
            continue
        previous = json.loads((upstream / 'runs' / f'{case["id"]}.json').read_text())
        rankings = [previous['rankings'][m]['12'] for m in protocol['upstream_methods']]
        candidates = fuse_rankings(rankings, 60)[:24]
        if any(not applicable(corpus[i]['scope'], case['patient']) for i in candidates):
            raise ValueError('Upstream applicability mismatch')
        question = focus_query(case['query'])
        key = hashlib.sha256(json.dumps([question, candidates]).encode()).hexdigest()
        tracer = Tracer(OUT / 'role_cache' / key, protocol['model'], gap=3)
        record = {'id': case['id'], 'family': case['family'], 'guideline': previous['guideline'],
                  'stage': 'development_only', 'question': question, 'candidate_ids': candidates,
                  'request_key': key, 'baseline_ids': candidates[:8]}
        try:
            chosen = select_passages(question, [corpus[i] for i in candidates], settings, llm=tracer)
            record.update({'available': True, 'selected_ids': chosen})
        except GenerationUnavailable as exc:
            if provider_failure(exc.code):
                save(OUT / 'pending_transport.json', {'id': case['id'], 'code': exc.code,
                     'messages': [c.get('provider_message') for c in tracer.calls if c.get('provider_message')],
                     'completed_cases': len(list((OUT / 'runs').glob('*.json'))),
                     'policy': 'No transport failure is scored as a clinical answer. Resume preserves completed requests.'})
                raise SystemExit(75)
            record.update({'available': False, 'selected_ids': [], 'completed_model_error': exc.code})
        except (ValueError, TypeError) as exc:
            record.update({'available': False, 'selected_ids': [], 'completed_contract_error': type(exc).__name__})
        record['calls'] = tracer.calls
        save(target, record)
        print('listwise development', case['id'], 'valid', record['available'],
              'selected', len(record['selected_ids']), flush=True)
    print('Development reranking saved. Final evaluation remains on hold.', flush=True)


if __name__ == '__main__':
    main()
