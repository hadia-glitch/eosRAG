"""Diagnose saved failures without changing or reinterpreting old outcomes."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'output/research/expanded100'
OUT = ROOT / 'output/research/rag_improvement_v1'


def main():
    counts = collections.Counter()
    examples = collections.defaultdict(list)
    for path in sorted((OLD / 'runs').glob('*.json')):
        row = json.loads(path.read_text(encoding='utf8'))
        result = row['result']
        counts['cases'] += 1
        counts['released'] += result['status'] == 'supported_for_review'
        counts['draft_missing'] += not bool(result.get('draft'))
        for call in row['calls']:
            if 'auditor' not in call['role']:
                continue
            reply = call.get('response')
            kind = None
            if call.get('error_code'):
                kind = 'auditor_transport_or_model_error'
            elif isinstance(reply, dict):
                if 'checked_claim_ids' not in reply:
                    kind = 'auditor_missing_checked_claim_ids'
                elif not isinstance(reply.get('reasons'), list):
                    kind = 'auditor_reasons_wrong_type'
            if kind:
                counts[kind] += 1
                examples[kind].append({'case': row['id'], 'role': call['role'], 'reply': reply})
        for error in result.get('errors', []):
            if 'numerical medication/fluid dosing' in error:
                counts['numerical_dose_guard_rejections'] += 1
    cases = json.loads((OLD / 'cases.json').read_text())
    counts['gold_passages'] = sum(len(c['gold_chunk_ids']) for c in cases)
    report = {'counts': dict(counts), 'examples': dict(examples),
              'precision_at_4_ceiling': counts['gold_passages'] / (4 * len(cases)),
              'old_input_sha256': hashlib.sha256((OLD / 'cases.json').read_bytes()).hexdigest(),
              'interpretation': 'Invalid audits remain invalid. Missing checked IDs are never backfilled. Fault rejection is desirable; unsafe fault release must remain zero in the challenge.'}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'failure_diagnosis.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in report.items() if k != 'examples'}, indent=2))


if __name__ == '__main__':
    main()
