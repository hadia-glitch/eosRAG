"""New v2 answer mode; patient-specific calls never share a retrieval cache."""
import argparse
import json
import time
from backend.scripts import evaluate_verification_improvements as runner
from backend.scripts.evaluate_rag_improvements import ROOT
from rag.source_answer import run_source_answer


def main(limit, wait=False):
    runner.OUT=ROOT/'output/research/rag_improvement_v2'
    runner.OLD=runner.OUT/'inputs'
    runner.run_verification=run_source_answer
    protocol={'primary_model':'openai/gpt-oss-120b','strict_schema':True,'max_repairs':1,
              'retrieval_variant':'expanded_rrf_ce_mmr','embedding_model':'sentence-transformers/all-MiniLM-L6-v2',
              'answer_mode':'Question-focused immutable source selections; patient findings remain separate',
              'design':'Post-hoc development candidate after a stopped four-case free-form pilot. Not a same-draft paired comparison or untouched test.',
              'planned_cases':100,'clinical_review':'pending'}
    path=runner.OUT/'answer_protocol.json'
    if path.exists() and runner.read(path)!=protocol:raise ValueError('Answer protocol drift')
    runner.save(path,protocol)
    cases=runner.read(runner.OLD/'cases.json')
    corpus={c['chunk_id']:c for c in runner.read(runner.OLD/'corpus.json')['chunks']}
    for case in cases[:limit]:
        path=runner.OUT/'retrieval/sentence-transformers__all-MiniLM-L6-v2'/f'{case["id"]}.json'
        deadline=time.monotonic()+1800
        while wait and not path.exists() and time.monotonic()<deadline:
            print('Waiting for retrieval:',case['id'],flush=True)
            time.sleep(30)
        if not path.exists():
            print('Retrieval not ready',case['id'],flush=True);continue
        rank=runner.read(path)
        selected=[corpus[k] for k in rank['rankings']['expanded_rrf_ce_mmr']]
        packet={'guideline':selected[0]['source']+'; EVALUATION ONLY','patient':case['patient'],
                'history':case['history'],'evaluation_question':case['query'],
                'evidence':[{'id':f'E{i+1}','chunk_id':c['chunk_id'],'text':c['raw_text'],
                             'source':c['source'],'version':c['version'],'page_number':c['pdf_page']} for i,c in enumerate(selected)]}
        runner.execute(case,packet,runner.OUT/'runs')
    runner.summarize()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=100);p.add_argument('--wait-for-retrieval',action='store_true')
    a=p.parse_args();main(a.limit,a.wait_for_retrieval)
