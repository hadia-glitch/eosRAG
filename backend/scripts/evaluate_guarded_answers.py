"""Final guarded-pipeline development run with lossless audit references."""
import argparse
import hashlib
import shutil
import time
from pathlib import Path
from backend.scripts import evaluate_verification_improvements as runner
from backend.scripts.evaluate_rag_improvements import ROOT
from rag.source_answer import run_source_answer
from rag.verification_v3 import compact_auditor


def verify(packet,settings,llm):
    result=run_source_answer(packet,settings,compact_auditor(llm))
    result['verification_version']='question-selection-plus-lossless-audit-v3'
    return result


def main(limit):
    runner.OUT=ROOT/'output/research/rag_improvement_v3'
    runner.OLD=ROOT/'output/research/rag_improvement_v2/inputs'
    runner.run_verification=verify
    protocol={'model':'openai/gpt-oss-120b','planned_cases':100,'retrieval_variant':'rrf_ce_mmr_guarded',
              'embedding_model':'sentence-transformers/all-MiniLM-L6-v2','strict_schema':True,'max_repairs':1,
              'temperature':0,'clinical_review':'pending','study_type':'Post-hoc development; no independent clinical test',
              'reuse':'Identical role+prompt+model completed outputs can replay verbatim, including dissent. No patient-specific sharing between distinct cases.',
              'code_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
                  'backend/rag/verification_v3.py','backend/rag/verification_v2.py','backend/rag/verification_graph.py',
                  'backend/rag/source_answer.py','backend/scripts/evaluate_guarded_answers.py']}}
    path=runner.OUT/'answer_protocol.json'
    if path.exists() and runner.read(path)!=protocol:raise ValueError('Guarded answer protocol drift')
    runner.save(path,protocol)
    cases=runner.read(runner.OLD/'cases.json')
    corpus={c['chunk_id']:c for c in runner.read(runner.OLD/'corpus.json')['chunks']}
    for case in cases[:limit]:
        rank_path=runner.OUT/'retrieval/sentence-transformers__all-MiniLM-L6-v2'/f'{case["id"]}.json'
        deadline=time.monotonic()+1800
        while not rank_path.exists() and time.monotonic()<deadline:
            print('Waiting for guarded retrieval:',case['id'],flush=True);time.sleep(30)
        if not rank_path.exists():raise SystemExit('Retrieval pending; resume this command')
        ranking=runner.read(rank_path)
        selected=[corpus[k] for k in ranking['rankings']['rrf_ce_mmr_guarded']]
        packet={'guideline':selected[0]['source']+'; EVALUATION ONLY','patient':case['patient'],'history':case['history'],
                'evaluation_question':case['query'],'evidence':[{'id':f'E{i+1}','chunk_id':c['chunk_id'],'text':c['raw_text'],
                    'source':c['source'],'version':c['version'],'page_number':c['pdf_page']} for i,c in enumerate(selected)]}
        prior=ROOT/'output/research/rag_improvement_v2/runs/role_cache'/case['id']
        target=runner.OUT/'runs/role_cache'/case['id']
        for saved in prior.glob('*.json'):
            data=runner.read(saved)
            if data.get('model')!='openai/gpt-oss-120b':continue
            target.mkdir(parents=True,exist_ok=True)
            if not (target/saved.name).exists():shutil.copy2(saved,target/saved.name)
        runner.execute(case,packet,runner.OUT/'runs')
    runner.summarize()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=100)
    main(p.parse_args().limit)
