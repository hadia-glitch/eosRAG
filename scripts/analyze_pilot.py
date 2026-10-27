"""Paired descriptive uncertainty and evaluator-quality audit; no new CSVs."""
import csv,json,re
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/research/phase1_pilot'

def rows(name):
    with (OUT/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def paired(records,key,left,right):
    values={}
    for r in records:
        if r['arm'] in {left,right} and r[key]!='NOT EVALUATED':
            values.setdefault(r['case_id'],{})[r['arm']]=float(r[key])
    pairs=[v[right]-v[left] for v in values.values() if set(v)=={left,right}]
    if not pairs:return {'n':0,'status':'NOT EVALUATED'}
    differences=np.array(pairs)
    rng=np.random.default_rng(20261025)
    means=differences[rng.integers(0,len(pairs),size=(20000,len(pairs)))].mean(axis=1)
    return {'n':len(pairs),'difference':f'{right} minus {left}',
            'mean_difference':float(differences.mean()),
            'bootstrap_percentile_95':[float(v) for v in np.quantile(means,[.025,.975])],
            'wins':int((differences>0).sum()),'ties':int((differences==0).sum()),
            'losses':int((differences<0).sum())}

def main():
    progress=json.loads((OUT/'progress.json').read_text())
    inputs=json.loads((OUT/'inputs.json').read_text())
    exact=rows('01_pilot_exact_retrieval.csv');gen=rows('05_pilot_generation.csv')
    usability=rows('04_pilot_clinical_usability.csv')
    comparisons={}
    for key in ['exact_mrr_at10','exact_ndcg_at10','anchor_grounding_recall']:
        comparisons['retrieval_'+key]=paired(exact,key,'dense','hybrid')
    for key in ['utility_precision_at10','semantic_mrr_at10','semantic_ndcg_at10']:
        comparisons[key]=paired(progress['semantic_per_case'],key,'dense','hybrid')
    for key in ['bleu','meteor','bertscore_f1']:
        comparisons[key]=paired(gen,key,'dense','hybrid')
    for key in ['clinical_utility','safety','faithfulness']:
        comparisons[key]=paired(usability,key,'dense','hybrid')
    stages={};suspect=[]
    for p in sorted((OUT/'judges').glob('*-rubric4-*.json')):
        j=json.loads(p.read_text())
        if not j.get('completed'):continue
        cid=j['case_id'];arm=j['mapping']['arm'];stage=j['evaluation_stage']
        stages.setdefault((cid,arm),{})[stage]=j['result']
        for field in ['unsupported_claims','contradictions','ungrounded_dose_examples']:
            for finding in j['result'].get(field,[]):
                text=finding.get('claim_text','')
                if not text or re.fullmatch(r'[A-Z /_-]+:',text.strip()) or len(text.split())<3:
                    suspect.append({'case_id':cid,'arm':arm,'stage':stage,'field':field,
                                    'finding':finding,'requires_independent_review':True})
    arms={};safety_rows=[]
    for (cid,arm),parts in stages.items():
        if set(parts)!={'grounding','clinical'}:continue
        safety_rows.append({'case_id':cid,'arm':arm,
            'regimen_incomplete':int(parts['clinical']['regimen_incomplete']),
            'ungrounded_dose':int(parts['grounding']['ungrounded_dose']),
            'unsupported_claim_plan':int(bool(parts['grounding']['unsupported_claims']))})
    for arm in ['dense_only','hybrid','dense_only_multiagent','hybrid_multiagent']:
        rs=[r for r in safety_rows if r['arm']==arm]
        arms[arm]={'n':len(rs),**{k:sum(r[k] for r in rs)/len(rs) if rs else 'NOT EVALUATED'
            for k in ['regimen_incomplete','ungrounded_dose','unsupported_claim_plan']}}
    for base,ma in [('dense_only','dense_only_multiagent'),('hybrid','hybrid_multiagent')]:
        for key in ['regimen_incomplete','ungrounded_dose','unsupported_claim_plan']:
            comparisons[base+'_versus_ma_'+key]=paired(safety_rows,key,base,ma)
    a={r['arm']:float(r['semantic_ndcg_at10']) for r in rows('03_pilot_semantic_summary.csv')}
    b={arm:float(np.mean([float(r['exact_ndcg_at10']) for r in exact if r['arm']==arm])) for arm in a}
    # All five means have distinct ranks in this pilot; fail rather than invent
    # a tie policy if a future input changes that assumption.
    assert len(set(a.values()))==len(a) and len(set(b.values()))==len(b)
    ar={k:i for i,k in enumerate(sorted(a,key=a.get))};br={k:i for i,k in enumerate(sorted(b,key=b.get))}
    rho=1-6*sum((ar[k]-br[k])**2 for k in a)/(len(a)*(len(a)**2-1))
    output={'seed':20261025,'bootstrap_replicates':20000,
        'uncertainty_scope':'Descriptive paired case bootstrap of ten development scenarios. Template/source dependence and selection from 30 eligible cases limit inference; no population-level clinical claim.',
        'complete_plan_population':progress['complete'],
        'input_scope_audit':{'missing_postnatal_age_case_ids':[c['case_id'] for c in inputs['cases']
            if c['risk_result']['patient'].get('age_hours') is None],
            'policy':'Missing age remains unknown in original judgments; corrected cases are separate and cannot repair original case scope.'},
        'paired_comparisons':comparisons,'safety_all_four_arms':arms,
        'exact_versus_semantic_ndcg_arm_rank_spearman':rho,
        'suspicious_evaluator_findings':suspect,
        'evaluator_audit_policy':'Preserve every completed final-rubric rating and finding. Suspect heading/empty-line findings are flagged for independent review, not silently deleted, rewritten or regraded.'}
    (OUT/'analysis.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'safety_completed_plans':len(safety_rows),
                     'suspicious_findings':len(suspect),'rank_spearman':rho}))

if __name__=='__main__':main()
