"""Development-only, label-blind clinical question decomposition.

The planner sees the question and selected guideline, never gold IDs,
engineering reference answers or retrieved candidate passages. Its output is
search text, never clinical evidence. Completed failures are retained.
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from pydantic import BaseModel,ConfigDict,Field

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from config import get_settings
from rag.relevance import focus_query
from rag.output_contracts import constrained_schema
from scripts.evaluate_expanded import Tracer
from scripts.evaluate_rag_improvements import save
from scripts.evaluation_transport import provider_failure
from services.groq_client import GenerationUnavailable

OUT=ROOT/'output/research/rag_development/query_planning'


class Plan(BaseModel):
    model_config=ConfigDict(extra='forbid')
    questions:list[str]=Field(min_length=1,max_length=3)


def plan_key(source,query):
    return hashlib.sha256(json.dumps([source,focus_query(query)]).encode()).hexdigest()


def main():
    cases=json.loads((ROOT/'output/research/expanded100/cases.json').read_text())
    routes={r['id']:r['guideline'] for r in json.loads((ROOT/'output/research/expanded100/manifest.json').read_text())['cases']}
    protocol={'stage':'development_only','model':'openai/gpt-oss-120b','temperature':0,'completion_tokens':1000,
        'inputs':'Focused question and selected guideline only. No gold IDs, references or candidate passages.',
        'output':'At most three clinical search questions, not answers, doses or guideline claims.',
        'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    path=OUT/'protocol.json'
    if path.exists() and json.loads(path.read_text())!=protocol:raise ValueError('Query-planning protocol drift')
    save(path,protocol)
    settings=get_settings().model_copy(update={'llm_provider':'groq','groq_model':protocol['model']})
    for case in cases:
        source=routes[case['id']];query=focus_query(case['query']);key=plan_key(source,query)
        target=OUT/'plans'/f'{key}.json'
        if target.exists():continue
        prompt=json.dumps({'task':
            'Decompose this clinical information need into one to three distinct short search QUESTIONS. '
            'Preserve negation, missingness and the requested clinical decision. Cover complementary '
            'assessment, investigation or treatment-review aspects only when required by the question. '
            'Use medical synonyms where helpful. Do not answer the questions, assert a guideline rule, '
            'introduce drugs, suggest numerical thresholds not in the question, invent patient facts '
            'or mention section/citation identifiers. Avoid generic filler and duplicate questions. '
            'These strings retrieve evidence from the selected source; they are not clinical advice.',
            'selected_guideline':source,'question':query,'output_schema':Plan.model_json_schema()})
        tracer=Tracer(OUT/'role_cache'/key,protocol['model'])
        try:
            response=tracer(prompt,settings,role='You are a clinical search question planner. Output search questions only.',
                completion_tokens=1000,response_schema=constrained_schema(Plan))
            plan=Plan.model_validate(response)
            allowed_numbers=set(re.findall(r'\d+(?:\.\d+)?',query))
            for question in plan.questions:
                if not 8<=len(question)<=400:raise ValueError('Invalid query length')
                if set(re.findall(r'\d+(?:\.\d+)?',question))-allowed_numbers:raise ValueError('Invented numeric query detail')
                if re.search(r'\b(?:NICE-|AAP2018-|WHO2024-|1\.\d+\.\d+)\b',question):raise ValueError('Citation identifier in query')
            save(target,{'source':source,'query':query,'available':True,'questions':plan.questions,
                         'calls':tracer.calls,'stage':'development_only'})
        except GenerationUnavailable as exc:
            if provider_failure(exc.code):
                save(OUT/'pending_transport.json',{'source':source,'query':query,'code':exc.code,
                    'messages':[c.get('provider_message') for c in tracer.calls if c.get('provider_message')]})
                raise SystemExit(75)
            save(target,{'source':source,'query':query,'available':False,'questions':[query],
                         'completed_model_error':exc.code,'calls':tracer.calls})
        except (ValueError,TypeError) as exc:
            save(target,{'source':source,'query':query,'available':False,'questions':[query],
                         'completed_contract_error':type(exc).__name__,'calls':tracer.calls})
        print('development query plan',source,key[:12],flush=True)


if __name__=='__main__':main()
