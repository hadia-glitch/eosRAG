"""Final 100-case task-aware audit study on frozen guarded retrieval."""
import argparse
import hashlib
import shutil
from backend.scripts import evaluate_verification_improvements as runner
from backend.scripts.evaluate_rag_improvements import ROOT
from rag.source_answer import run_source_answer
from rag.verification_v4 import task_aware_auditor


def main(limit):
    out=ROOT/'output/research/rag_improvement_v4'
    from scripts.evaluate_rag_improvements import save
    protocol={'planned_cases':100,'model':'openai/gpt-oss-120b','retrieval':'frozen v3 MiniLM rrf_ce_mmr_guarded',
              'change':'Exact evaluation question and task mode are supplied to both independent auditors.',
              'design':'Post-hoc development. Earlier pilot decisions retained separately; no untouched-test claim.',
              'clinical_review':'pending','max_repairs':1,'strict_schema':True,
              'code_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
                  'backend/rag/verification_v4.py','backend/rag/verification_v3.py','backend/rag/verification_v2.py',
                  'backend/rag/verification_graph.py','backend/rag/source_answer.py','backend/scripts/evaluate_task_aware_answers.py']}}
    path=out/'answer_protocol.json'
    if path.exists() and runner.read(path)!=protocol:raise ValueError('Task-aware answer protocol drift')
    save(path,protocol)
    runner.OUT=out
    runner.OLD=ROOT/'output/research/rag_improvement_v2/inputs'
    def verify(packet,settings,llm):
        result=run_source_answer(packet,settings,task_aware_auditor(llm,{**packet,'task_mode':'care_plan'}))
        result['verification_version']='question-focused-task-aware-v4'
        return result
    runner.run_verification=verify
    cases=runner.read(runner.OLD/'cases.json')
    corpus={c['chunk_id']:c for c in runner.read(runner.OLD/'corpus.json')['chunks']}
    for case in cases[:limit]:
        rank=ROOT/'output/research/rag_improvement_v3/retrieval/sentence-transformers__all-MiniLM-L6-v2'/f'{case["id"]}.json'
        if not rank.exists():raise SystemExit('Guarded retrieval incomplete: '+case['id'])
        selected=[corpus[k] for k in runner.read(rank)['rankings']['rrf_ce_mmr_guarded']]
        packet={'guideline':selected[0]['source']+'; EVALUATION ONLY','patient':case['patient'],'history':case['history'],
                'evaluation_question':case['query'],'evidence':[{'id':f'E{i+1}','chunk_id':c['chunk_id'],'text':c['raw_text'],
                    'source':c['source'],'version':c['version'],'page_number':c['pdf_page']} for i,c in enumerate(selected)]}
        folder=out/'runs'
        for version in [2,3]:
            prior=ROOT/f'output/research/rag_improvement_v{version}/runs/role_cache'/case['id']
            target=folder/'role_cache'/case['id']
            for old in prior.glob('*.json'):
                if runner.read(old).get('model')!='openai/gpt-oss-120b':continue
                target.mkdir(parents=True,exist_ok=True)
                if not (target/old.name).exists():shutil.copy2(old,target/old.name)
        runner.execute(case,packet,folder)
    runner.summarize()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=100)
    main(p.parse_args().limit)
