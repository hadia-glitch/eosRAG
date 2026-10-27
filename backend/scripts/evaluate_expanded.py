"""Resumable orchestration adapters; frozen retrieval/generation code is untouched."""
from __future__ import annotations
import argparse
import contextlib
import copy
import hashlib
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from scripts.prepare_expanded_benchmark import OUT, save, sha
OUT = ROOT / 'output/research/expanded100'

def read(path):
    return json.loads(path.read_text(encoding='utf8'))

def validate():
    manifest, protocol = read(OUT/'manifest.json'), read(OUT/'protocol.json')
    for name, key in [('cases.json','cases_file_sha256'),('corpus.json','corpus_file_sha256'),('protocol.json','protocol_sha256')]:
        assert sha((OUT/name).read_bytes()) == manifest[key], f'Frozen input drift: {name}'
    assert sha((ROOT/'output/research/rag_v2/cases.json').read_bytes()) == manifest['original_cases_file_sha256'], 'Original 18 changed'
    for path, digest in protocol['code_sha256'].items():
        assert sha((ROOT/path).read_bytes()) == digest, f'Frozen code drift: {path}'
    return read(OUT/'cases.json'), read(OUT/'corpus.json')['chunks'], protocol

def retrieval():
    from scripts import evaluate_generation as original
    cases, corpus, _ = validate()
    combined = []
    for guideline in ['NICE','AAP','WHO']:
        selected = [c for c in cases if c['gold_chunk_ids'][0].startswith(guideline)]
        original.OUT = OUT / 'retrieval' / guideline
        results = original.retrieve(selected, [c for c in corpus if c['guideline_id']==guideline])
        combined.extend(results)
        print('retrieval', guideline, len(selected), read(original.OUT/'retrieval.json')['summary'], flush=True)
    save(OUT/'retrieval.json', {'cases':combined,'protocol':'Source-gated unchanged evaluate_generation.retrieve; RRF60, top4'})
    old = read(ROOT/'output/research/rag_v2/retrieval.json')['cases']
    ranks = {r['id']:r['rankings'] for r in combined}
    differences = [r['id'] for r in old if r['rankings'] != ranks[r['id']]]
    save(OUT/'retrieval_replay_check.json', {'original_cases':len(old),'changed_rankings':differences,
        'interpretation':'No retrieval tuning. Drift is disclosed if encoder/package/runtime changes affect rankings.'})

class Tracer:
    cloud_lock = threading.Lock()
    cloud_next_call = 0.
    def __init__(self, folder, model, gap=0, injected=None):
        self.folder, self.model, self.gap, self.injected = folder, model, gap, injected
        self.calls = []
        self.lock = threading.Lock()
        self.counter = {}
        self.last = 0.
        self.quota = False

    def __call__(self, prompt, settings, **kw):
        from services.groq_client import complete_json, GenerationUnavailable
        from scripts.evaluation_transport import provider_failure
        role = kw['role']
        key = sha((role+'\n'+prompt).encode())
        with self.lock:
            occurrence = self.counter.get(key, 0)
            self.counter[key] = occurrence + 1
        path = self.folder/f'{key}-{occurrence}.json'
        if path.exists():
            old = read(path)
            self.calls.append({**old, 'replayed':True})
            if 'response' in old:
                return old['response']
            raise GenerationUnavailable('Cached completed model failure', old['error_code'])
        entry = {'role':role,'model':kw.get('model',self.model),'prompt_sha256':sha(prompt.encode()),
                 'occurrence':occurrence,'prompt':prompt,'completion_tokens':kw.get('completion_tokens',3000)}
        started = time.monotonic()
        try:
            if self.injected is not None and role == 'You are the evidence synthesis agent.':
                response = copy.deepcopy(self.injected)
                entry['injected'] = True
            else:
                # Serialization preserves the declared backbone call gap. This is
                # operational pacing, not repeated sampling for better answers.
                with self.cloud_lock if self.gap else contextlib.nullcontext():
                    if self.quota:
                        raise GenerationUnavailable('Quota stop', 'http_429')
                    delay = self.cloud_next_call-time.monotonic() if self.gap else 0.
                    if delay > 0:
                        time.sleep(delay)
                    try:
                        for attempt in range(4):
                            try:
                                response = complete_json(prompt, settings, **kw)
                                break
                            except GenerationUnavailable as exc:
                                cause = exc.__cause__
                                message = ''
                                if getattr(cause,'response',None) is not None:
                                    try:
                                        message = str(cause.response.json().get('error',{}).get('message',''))
                                    except ValueError:
                                        pass
                                daily = 'tokens per day' in message.lower() or '(tpd)' in message.lower()
                                retryable = exc.code in {'http_429','http_500','http_502','http_503','http_504'}
                                if not retryable or daily or attempt==3:
                                    raise
                                save(ROOT/'output/operational/expanded_retries'/f'{time.time_ns()}.json',
                                     {'role':role,'model':kw.get('model',self.model),'error_code':exc.code,
                                      'attempt':attempt+1,'provider_message':message[:1500]})
                                delay = (exc.retry_after_seconds or 30)+2
                                print('transport_retry',exc.code,'wait_seconds',round(delay,1),flush=True)
                                deadline=time.monotonic()+delay
                                while time.monotonic()<deadline:
                                    time.sleep(min(5,deadline-time.monotonic()))
                    finally:
                        self.last = time.monotonic()
                        if self.gap:
                            Tracer.cloud_next_call = self.last+self.gap
            entry['response'] = response
            return response
        except GenerationUnavailable as exc:
            entry['error_code'] = exc.code
            cause = exc.__cause__
            provider_error={}
            if getattr(cause, 'response', None) is not None:
                try:
                    provider_error=cause.response.json().get('error',{})
                    entry['provider_message'] = str(provider_error.get('message',''))[:1500]
                except ValueError:
                    pass
            if exc.code=='http_400' and (provider_error.get('code')=='json_validate_failed' or
                ('failed_generation' in provider_error and 'failed to generate json' in str(provider_error.get('message','')).lower())):
                entry['provider_original_error_code']='http_400'
                entry['error_code']='model_json_contract_failure'
                entry['raw_failed_generation']=provider_error.get('failed_generation')
                raise GenerationUnavailable('Completed model JSON contract failure','model_json_contract_failure') from exc
            if exc.code == 'http_429':
                self.quota = True
            if provider_failure(exc.code):
                save(ROOT/'output/operational/expanded'/f'{time.time_ns()}.json', entry)
            raise
        finally:
            entry['seconds'] = time.monotonic()-started
            self.calls.append(entry)
            # Completed malformed responses are cached too; outages are not.
            if 'response' in entry or ('error_code' in entry and not provider_failure(entry['error_code'])):
                save(path, entry)

def settings_for(model, repairs=0, budget=120.):
    from config import get_settings
    return get_settings().model_copy(update={'llm_provider':'groq','verifier_provider':'groq',
        'groq_model':model,'verifier_model':model,'verification_max_repairs':repairs,
        'llm_schema_enforcement':False,'verification_budget_seconds':budget})

def hydrate_completed_calls(record, folder):
    """Recover a semantic-error checkpoint from an older transport classifier."""
    from scripts.evaluation_transport import provider_failure
    for call in record.get('calls',[]):
        if not call.get('prompt') or ('response' not in call and provider_failure(call.get('error_code'))):
            continue
        key=sha((call['role']+'\n'+call['prompt']).encode())
        path=folder/'role_cache'/record['id']/f'{key}-{call.get("occurrence",0)}.json'
        if not path.exists():
            save(path,call)

def run_case(case, packet, model, folder, repairs=0, gap=0, injected=None, budget=120.):
    from rag.verification_graph import run_verification
    from scripts.evaluation_transport import quality_eligible
    path = folder/f'{case["id"]}.json'
    if path.exists() and quality_eligible(read(path)):
        previous=read(path)
        hydrate_completed_calls(previous,folder)
        return previous
    settings = settings_for(model, repairs, budget)
    trace = Tracer(folder/'role_cache'/case['id'], model, gap, injected)
    started = time.monotonic()
    result = run_verification(packet, settings, llm=trace)
    record = {'id':case['id'],'family':case['family'],'model':model,'verifier_model':model,
              'seconds':time.monotonic()-started,'calls':trace.calls,'packet':packet,'result':result,
              'settings':{'temperature':0,'sampling_seed':None,'repairs':repairs,'budget_seconds':budget,
                          'schema_enforcement':False,'timeout_seconds':settings.llm_timeout_seconds,'call_gap_seconds':gap},
              'verification_source_sha256':sha((ROOT/'backend/rag/verification_graph.py').read_bytes())}
    save(path, record)
    print(model, case['id'], result['status'], 'quality_eligible', quality_eligible(record), flush=True)
    if not quality_eligible(record):
        save(OUT/'pending_transport.json', {'case':case['id'],'model':model,
             'codes':[c.get('error_code') for c in trace.calls if c.get('error_code')],
             'messages':[c.get('provider_message') for c in trace.calls if c.get('provider_message')],
             'instruction':'Resume same command after quota/availability restored. Completed roles remain saved.'})
        raise SystemExit(75)
    return record

def packets():
    cases, corpus, protocol = validate()
    byid = {c['chunk_id']:c for c in corpus}
    ranks = {r['id']:r for r in read(OUT/'retrieval.json')['cases']}
    for case in cases:
        selected = [byid[key] for key in ranks[case['id']]['rankings']['hybrid_concepts']]
        guideline = selected[0]['guideline_id']
        source_name = {'AAP':'AAP 2018 >=35 weeks','NICE':'NICE NG195 (2026)','WHO':'WHO serious bacterial infections 2024 (EOS subset)'}[guideline]
        packet = {'guideline':source_name+', EVALUATION ONLY',
                  'patient':case['patient'],'history':case['history'],'evaluation_question':case['query'],
                  'evidence':[{'id':f'E{i+1}','chunk_id':c['chunk_id'],'text':c['text'],'source':c['source'],
                               'version':c['version'],'page_number':c['pdf_page']} for i,c in enumerate(selected)]}
        yield case, packet, protocol

def primary():
    for case, packet, protocol in packets():
        run_case(case, packet, protocol['primary_model'], OUT/'runs')

def faults():
    _, corpus, protocol = validate()
    byid = {c['chunk_id']:c for c in corpus}
    specs = [('negation','NICE-1.15.3','AAP2018-35PLUS-P6-B2','C-reactive protein results alone are sufficient to decide to stop antibiotics.'),
             ('missing_conditions','NICE-1.21.3','AAP2018-35PLUS-SP6','A negative culture at 36 hours guarantees antibiotics can be stopped even when the baby still has respiratory distress.'),
             ('invented_dose','NICE-1.13.1','AAP2018-35PLUS-SP5','Give gentamicin 99 mg/kg immediately without obtaining a blood culture.'),
             ('false_normal','NICE-1.10.1','AAP2018-35PLUS-SP2','The unrecorded maternal history and vital signs are normal, so infection has been excluded.')]
    who_keys = {'negation':'WHO2024-A.1','missing_conditions':'WHO2024-B.2','invented_dose':'WHO2024-B.2','false_normal':'WHO2024-A.1'}
    for guideline in ['NICE','AAP','WHO']:
        for family, nice, aap, text in specs:
            source = byid[nice if guideline=='NICE' else aap if guideline=='AAP' else who_keys[family]]
            for variant in range(3):
                case = {'id':f'{guideline}-{family}-{variant+1}','family':family}
                packet = {'guideline':guideline+' evaluation only','patient':{'age_hours':12+variant*6,
                    'gestational_age_weeks':35+variant,'respiratory_distress':True,'maternal_history':'unknown'},'history':[],
                    'evidence':[{'id':'E1','text':source['text'],'chunk_id':source['chunk_id'],'source':source['source'],'version':source['version']}]}
                draft = {'claims':[{'id':'C1','section':'recommended_actions','text':text,
                    'support':[{'evidence_id':'E1','quote':source['text'][:180]}]}]}
                run_case(case,packet,protocol['primary_model'],OUT/'stress',injected=draft)

def judges():
    from scripts.evaluation_transport import quality_eligible,provider_failure
    from services.groq_client import GenerationUnavailable
    for case, _, protocol in packets():
        run_path = OUT/'runs'/f'{case["id"]}.json'
        if not run_path.exists():
            continue
        run = read(run_path)
        if not quality_eligible(run):
            continue
        path = OUT/'judges'/f'{case["id"]}.json'
        if path.exists():
            continue
        text = ' '.join(c['text'] for c in run['result'].get('draft',{}).get('claims',[]))
        if not text:
            save(path, {'available':False,'reason':'no draft'})
            continue
        prompt = json.dumps({'task':'Blind research evaluation. Score this candidate against patient facts, guideline passages and reference. Do not infer clinical correctness from fluency or text overlap. Return integer 1-5 for grounding, patient_fidelity, completeness, actionability, uncertainty (5=best). Also return unsafe_claim_count integer >=0 and brief reasons. Missing facts must not be assumed normal. This is a synthetic engineering test, not clinician validation.',
                             'candidate':text,'case':case,'guidelines':run['packet']['evidence']})
        tracer = Tracer(OUT/'judge_cache'/case['id'],protocol['primary_model'])
        try:
            result = tracer(prompt,settings_for(protocol['primary_model']),role='You are a blinded evaluation judge. You did not generate or audit this candidate.')
            valid = all(type(result.get(k)) is int and 1<=result[k]<=5 for k in ['grounding','patient_fidelity','completeness','actionability','uncertainty'])
            valid &= type(result.get('unsafe_claim_count')) is int and result['unsafe_claim_count']>=0
            save(path,{'available':bool(valid),'model':protocol['primary_model'],'scores':result,'reason':None if valid else 'invalid judge scores'})
        except GenerationUnavailable as exc:
            if provider_failure(exc.code):
                print('Judge transport incomplete; resume after availability restored.',flush=True)
                raise SystemExit(75)
            save(path,{'available':False,'model':protocol['primary_model'],'reason':exc.code,
                       'completed_model_failure':True})
        print('judge',case['id'],flush=True)

def backbones():
    import shutil
    for case, packet, protocol in packets():
        for model in protocol['backbone_models']:
            label = model.replace('/','_')
            base_folder = OUT/'backbones'/label/'no_repair'
            base = run_case(case,packet,model,base_folder,gap=20)
            resolved_folder = OUT/'backbones'/label/'one_repair'
            source_cache = base_folder/'role_cache'/case['id']
            destination = resolved_folder/'role_cache'/case['id']
            if source_cache.exists():
                shutil.copytree(source_cache,destination,dirs_exist_ok=True)
            # The graph still applies its original budget predicate; replay must
            # not turn elapsed initial work into free resolution time.
            budget = max(0.,120.-base['seconds'])
            run_case(case,packet,model,resolved_folder,repairs=1,gap=20,budget=budget)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['retrieval','primary','faults','judges','backbones','all'])
    args = parser.parse_args()
    modes = ['retrieval','primary','faults','judges','backbones'] if args.mode=='all' else [args.mode]
    for mode in modes:
        globals()[mode]()
