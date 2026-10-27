"""Validate source/case hashes and prove paired arms reuse initial model outcomes."""
import argparse
from pathlib import Path
from backend.scripts.prepare_expanded_benchmark import canonical,sha,save
from backend.scripts.evaluate_expanded import OUT,read,validate
from backend.scripts.evaluation_transport import quality_eligible

def check(allow_pending=False):
    cases,corpus,protocol=validate()
    manifest=read(OUT/'manifest.json')
    meta={r['id']:r for r in manifest['cases']}
    index={r['chunk_id']:r for r in corpus}
    assert len(cases)==len(meta)==100
    for case in cases:
        assert sha(canonical(case))==meta[case['id']]['sha256'],f'Case hash drift: {case["id"]}'
        for gold in meta[case['id']]['gold']:
            assert gold['id'] in index,f'MISSING GOLD ID {gold["id"]}'
            assert sha(index[gold['id']]['text'].encode())==gold['text_sha256']
    primary=[read(OUT/'runs'/f'{c["id"]}.json') for c in cases]
    assert all(quality_eligible(r) for r in primary),'Primary provider execution incomplete'
    faults=[read(p) for p in (OUT/'stress').glob('*.json')]
    assert len(faults)==36 and all(quality_eligible(r) for r in faults)
    assert all((OUT/'judges'/f'{c["id"]}.json').exists() for c in cases)
    paired=0
    pending=[]
    for model in protocol['backbone_models']:
        folder=OUT/'backbones'/model.replace('/','_')
        for case in cases:
            paths=[folder/arm/f'{case["id"]}.json' for arm in ['no_repair','one_repair']]
            if not all(p.exists() for p in paths):
                pending.append([model,case['id']]);continue
            before,after=[read(p) for p in paths]
            if not all(quality_eligible(r) for r in [before,after]):
                pending.append([model,case['id']]);continue
            assert before['packet']==after['packet'],f'Paired packet changed: {model} {case["id"]}'
            trace=after['result'].get('resolution_trace',[])
            assert len(trace)<=1
            initial=trace[0] if trace else after['result']
            for key in ['draft','evidence_verdict','safety_verdict','status','errors']:
                assert before['result'].get(key)==initial.get(key),f'Initial outcome resampled: {model} {case["id"]} {key}'
            def signature(call):
                return call['role'],call['prompt_sha256'],call.get('occurrence',0)
            after_calls={signature(c):c for c in after['calls']}
            for call in before['calls']:
                key=signature(call)
                assert key in after_calls,f'Initial role missing: {model} {case["id"]} {key}'
                other=after_calls[key]
                assert call.get('response')==other.get('response') and call.get('error_code')==other.get('error_code'),f'Completed role replaced: {model} {case["id"]}'
            assert sum('resolution agent' in c['role'] for c in after['calls'])<=1
            paired+=1
    report={'unique_cases':100,'primary_quality_complete':100,'fault_quality_complete':36,
        'judge_stages_complete':100,'paired_initial_outcomes_checked':paired,'planned_pairs':200,
        'pending_pairs':pending,'completed_pairs_reuse_initial_outcomes':True,'all_declared_work_complete':not pending}
    save(OUT/'integrity_report.json',report)
    if pending and not allow_pending:
        raise SystemExit(f'{len(pending)} pairs remain incomplete; final integrity release refused')
    print({k:v for k,v in report.items() if k!='pending_pairs'})

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--allow-pending',action='store_true')
    check(parser.parse_args().allow_pending)
