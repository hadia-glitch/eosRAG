"""CSV tables with paired case and scenario-family bootstrap uncertainty."""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.evaluate_expanded import OUT, read, validate
from scripts.prepare_expanded_benchmark import save
TABLES=OUT/'tables'
SEED=31
B=2000

def table(name, rows):
    TABLES.mkdir(parents=True,exist_ok=True)
    if not rows:
        return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (TABLES/(name+'.csv')).open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def ci(values, families):
    values=np.asarray(values,dtype=float)
    if not len(values):
        return {'mean':None,'case_low':None,'case_high':None,'family_low':None,'family_high':None,'family_n':0,'resamples':B,'seed':SEED}
    rng=np.random.default_rng(SEED)
    draws=values[rng.integers(0,len(values),(B,len(values)))].mean(axis=1)
    unique=sorted(set(families))
    sums=np.array([values[np.array(families)==family].sum() for family in unique])
    counts=np.array([sum(f==family for f in families) for family in unique])
    ix=rng.integers(0,len(unique),(B,len(unique)))
    # Resample entire families and retain all their members. Unequal family
    # sizes are therefore weighted by their actual resampled case counts.
    clustered=sums[ix].sum(axis=1)/counts[ix].sum(axis=1)
    return {'mean':float(values.mean()),'case_low':float(np.quantile(draws,.025)),
            'case_high':float(np.quantile(draws,.975)),'family_low':float(np.quantile(clustered,.025)),
            'family_high':float(np.quantile(clustered,.975)),'family_n':len(unique),'resamples':B,'seed':SEED}

def retrieval_tables():
    cases,_,_=validate()
    byid={c['id']:c for c in cases}
    guideline={r['id']:r['guideline'] for r in read(OUT/'manifest.json')['cases']}
    rankings=read(OUT/'retrieval.json')['cases']
    rows=[]
    for record in rankings:
        case=byid[record['id']]
        for method,ids in record['rankings'].items():
            gold=set(case['gold_chunk_ids'])
            rows.append({'case_id':case['id'],'family':case['family'],'guideline':guideline[case['id']],
                         'method':method,'recall_at_4':len(set(ids)&gold)/len(gold),
                         'mrr_at_4':next((1/(i+1) for i,key in enumerate(ids) if key in gold),0.),
                         'ranked_ids':'|'.join(ids),'gold_ids':'|'.join(case['gold_chunk_ids'])})
    table('retrieval_per_case',rows)
    summaries,paired=[],[]
    for g in ['NICE','AAP','WHO']:
        group=[r for r in rows if r['guideline']==g]
        for method in ['lexical','dense','hybrid','hybrid_concepts']:
            selected=[r for r in group if r['method']==method]
            for metric in ['recall_at_4','mrr_at_4']:
                summaries.append({'guideline':g,'method':method,'metric':metric,'n':len(selected),
                                  **ci([r[metric] for r in selected],[r['family'] for r in selected])})
        for metric in ['recall_at_4','mrr_at_4']:
            left={r['case_id']:r for r in group if r['method']=='hybrid'}
            right=[r for r in group if r['method']=='hybrid_concepts']
            paired.append({'guideline':g,'contrast':'hybrid_concepts minus hybrid','metric':metric,'n':len(right),
                           **ci([r[metric]-left[r['case_id']][metric] for r in right],[r['family'] for r in right])})
    table('retrieval_by_guideline',summaries)
    table('retrieval_paired_differences',paired)
    return summaries,paired

def score_alignment(saved_only=False):
    from scripts import evaluate_generation as original
    from scripts.evaluation_transport import quality_eligible
    cases,_,_=validate()
    missing=[c['id'] for c in cases if not (OUT/'runs'/f'{c["id"]}.json').exists() or not quality_eligible(read(OUT/'runs'/f'{c["id"]}.json'))]
    if missing and not saved_only:
        raise SystemExit(f'Alignment scoring requires completed transport for every planned case; {len(missing)} pending. No missing cases silently scored zero.')
    original.OUT=OUT
    if saved_only:
        completed=[c for c in cases if c['id'] not in missing]
        if not completed:
            raise SystemExit('No completed cases to score')
        original_load=original.load
        original.load=lambda name: completed if name=='cases.json' else original_load(name)
        save(OUT/'score_snapshot_manifest.json',{'planned_n':100,'completed_snapshot_n':len(completed),
            'completed_case_ids':[c['id'] for c in completed], 'pending_case_ids':missing,
            'metric_policy':'Same frozen original scoring function and configurations; no absent/provider-failed cases are imputed zero.'})
    original.score()
    original.refresh_judges()
    qualify_legacy_summary()

def qualify_legacy_summary():
    legacy=read(OUT/'summary.json')
    save(OUT/'intermediates/legacy_score_snapshot.json',legacy)
    legacy.update({'planned_n':100,'completed_snapshot_n':legacy['n'],'pending_n':100-legacy['n'],
                   'analysis_status':'complete_primary' if legacy['n']==100 else 'partial_not_for_manuscript',
                   'publication_tables_file':'tables_summary.json',
                   'note':'Pooled legacy diagnostics are preserved for replay only. Source-stratified CSV tables are authoritative; conditional coverage is relative to the quality population.'})
    for arm,values in legacy['arms'].items():
        emitted=legacy['generated'] if arm.startswith('without_verification') else legacy['released']
        values.update({'emitted':emitted,'coverage_denominator':legacy['n'],'coverage':emitted/legacy['n']})
        if not values['judge_n']:
            values['judge_unsafe_claims']=None
    save(OUT/'summary.json',legacy)

def refresh_saved_judges():
    if not (OUT/'per_case_metrics.json').exists():
        return
    from scripts import evaluate_generation as original
    original.OUT=OUT
    original.refresh_judges()
    qualify_legacy_summary()

def alignment_tables():
    if not (OUT/'per_case_metrics.json').exists():
        return [],[]
    records=read(OUT/'per_case_metrics.json')
    guideline={r['id']:r['guideline'] for r in read(OUT/'manifest.json')['cases']}
    per_case=[]
    for r in records:
        for metric,value in r['metrics'].items():
            per_case.append({'case_id':r['id'],'family':r['family'],'guideline':guideline[r['id']],
                             'metric':metric,'without_verification':value,
                             'with_verification':value if r['released'] else 0.,'released':int(r['released']),
                             'generated':int(bool(r['candidate'])),'quality_n':1,
                             'unverified_emitted':int(bool(r['candidate'])),'verified_emitted':int(r['released']),
                             'unverified_coverage':int(bool(r['candidate'])),'verified_coverage':int(r['released'])})
    table('alignment_per_case',per_case)
    summaries,paired=[],[]
    planned=read(OUT/'protocol.json')['guideline_counts']
    for g in ['NICE','AAP','WHO']:
        group=[r for r in records if guideline[r['id']]==g]
        if not group:
            continue
        released=sum(r['released'] for r in group)
        generated=sum(bool(r['candidate']) for r in group)
        families=[r['family'] for r in group]
        for metric in group[0]['metrics']:
            for arm in ['without_verification','verified_all_cases','released_only','generated_only']:
                selected=[r for r in group if r['released']] if arm=='released_only' else [r for r in group if r['candidate']] if arm=='generated_only' else group
                values=[r['metrics'][metric] if arm!='verified_all_cases' or r['released'] else 0. for r in selected]
                emitted=generated if arm in ['without_verification','generated_only'] else released
                summaries.append({'guideline':g,'arm':arm,'metric':metric,'planned_n':planned[g],'quality_n':len(group),
                    'generated':generated,'released':released,'scored_n':len(selected),'emitted':emitted,
                    'coverage':emitted/len(group),'coverage_denominator':len(group),
                    **ci(values,[r['family'] for r in selected])})
            paired.append({'guideline':g,'contrast':'verified minus unverified, all completed cases',
                'metric':metric,'n':len(group),'generated':generated,'released':released,'coverage':released/len(group),
                **ci([r['metrics'][metric]*(int(r['released'])-1) for r in group],families)})
        # BLEU sufficient statistics allow an authentic corpus score for every
        # bootstrap resample, rather than averaging sentence BLEU.
        from sacrebleu.metrics import BLEU
        bleu=BLEU(tokenize='13a',smooth_method='exp')
        def corpus_stats(text,reference):
            return bleu._extract_corpus_statistics([text],[[reference]])[0]
        references=[r['reference'] for r in group]
        unverified=np.array([corpus_stats(r['candidate'],r['reference']) for r in group])
        verified=np.array([corpus_stats(r['candidate'] if r['released'] else '',r['reference']) for r in group])
        def corpus_value(stats):
            s=stats.sum(axis=0).tolist()
            return BLEU.compute_bleu(correct=s[2:6],total=s[6:10],sys_len=s[0],ref_len=s[1],smooth_method='exp').score/100
        rng=np.random.default_rng(SEED)
        indices=rng.integers(0,len(group),(B,len(group)))
        family_set=sorted(set(families))
        clusters=[[i for i,f in enumerate(families) if f==x] for x in family_set]
        cluster_indices=[np.concatenate([clusters[j] for j in rng.integers(0,len(clusters),len(clusters))]) for _ in range(B)]
        selected_released=np.array([i for i,r in enumerate(group) if r['released']],dtype=int)
        selected_generated=np.array([i for i,r in enumerate(group) if r['candidate']],dtype=int)
        variants=[('without_verification',unverified,np.arange(len(group))),
                  ('verified_all_cases',verified,np.arange(len(group))),
                  ('released_only',unverified[selected_released],selected_released),
                  ('generated_only',unverified[selected_generated],selected_generated)]
        for arm,stats,selection in variants:
            n=len(selection)
            rng_arm=np.random.default_rng(SEED)
            arm_indices=rng_arm.integers(0,n,(B,n)) if n else []
            arm_families=[families[i] for i in selection]
            arm_unique=sorted(set(arm_families))
            arm_clusters=[[i for i,family in enumerate(arm_families) if family==name] for name in arm_unique]
            arm_cluster_indices=[np.concatenate([arm_clusters[j] for j in rng_arm.integers(0,len(arm_clusters),len(arm_clusters))]) for _ in range(B)] if n else []
            draws=[corpus_value(stats[ix]) for ix in arm_indices]
            family_draws=[corpus_value(stats[ix]) for ix in arm_cluster_indices]
            emitted=generated if arm in ['without_verification','generated_only'] else released
            summaries.append({'guideline':g,'arm':arm,'metric':'corpus_bleu4','planned_n':planned[g],
                'quality_n':len(group),'generated':generated,'released':released,'scored_n':n,'emitted':emitted,
                'coverage':emitted/len(group),'coverage_denominator':len(group),'mean':corpus_value(stats) if n else None,
                'case_low':float(np.quantile(draws,.025)) if n else None,'case_high':float(np.quantile(draws,.975)) if n else None,
                'family_low':float(np.quantile(family_draws,.025)) if n else None,'family_high':float(np.quantile(family_draws,.975)) if n else None,
                'family_n':len(arm_unique),'resamples':B,'seed':SEED})
        deltas=[corpus_value(verified[ix])-corpus_value(unverified[ix]) for ix in indices]
        family_deltas=[corpus_value(verified[ix])-corpus_value(unverified[ix]) for ix in cluster_indices]
        paired.append({'guideline':g,'contrast':'verified minus unverified, all completed cases','metric':'corpus_bleu4',
            'n':len(group),'generated':generated,'released':released,'coverage':released/len(group),
            'mean':corpus_value(verified)-corpus_value(unverified),
            'case_low':float(np.quantile(deltas,.025)),'case_high':float(np.quantile(deltas,.975)),
            'family_low':float(np.quantile(family_deltas,.025)),'family_high':float(np.quantile(family_deltas,.975)),
            'resamples':B,'seed':SEED})
    table('alignment_by_guideline',summaries)
    table('alignment_paired_differences',paired)
    # The unchanged cases provide a population-matched historical control.
    # Runtime/model-service drift still prevents a causal before/after claim.
    original_ids={c['id'] for c in read(ROOT/'output/research/rag_v2/cases.json')}
    control=[r for r in records if r['id'] in original_ids]
    control_rows=[]
    for arm in ['without_verification','verified_all_cases','released_only','generated_only']:
        selected=[r for r in control if r['released']] if arm=='released_only' else [r for r in control if r['candidate']] if arm=='generated_only' else control
        emitted=sum(bool(r['candidate']) for r in control) if arm in ['without_verification','generated_only'] else sum(r['released'] for r in control)
        for metric in control[0]['metrics'] if control else []:
            control_rows.append({'guideline':'NICE_original18','arm':arm,'metric':metric,
                'planned_n':18,'quality_n':len(control),'scored_n':len(selected),'emitted':emitted,
                'generated':sum(bool(r['candidate']) for r in control),'released':sum(r['released'] for r in control),
                'coverage':emitted/len(control),
                **ci([r['metrics'][metric] if arm!='verified_all_cases' or r['released'] else 0. for r in selected],[r['family'] for r in selected])})
    table('original18_control',control_rows)
    judged=[]
    for g in ['NICE','AAP','WHO']:
        group=[r for r in records if guideline[r['id']]==g]
        for arm in ['without_verification','with_verification']:
            selected=[r for r in group if r['judge'].get('available') and (arm=='without_verification' or r['released'])]
            for metric in ['grounding','patient_fidelity','completeness','actionability','uncertainty','unsafe_claim_count']:
                judged.append({'guideline':g,'arm':arm,'metric':metric,'quality_n':len(group),'judge_n':len(selected),
                    'generated':sum(bool(r['candidate']) for r in group),'released':sum(r['released'] for r in group),
                    'coverage':len(selected)/len(group) if group else None,
                    'observed_sum':sum(r['judge']['scores'][metric] for r in selected),
                    **ci([r['judge']['scores'][metric] for r in selected],[r['family'] for r in selected])})
    table('judge_by_guideline',judged)
    return summaries,paired

def fault_tables():
    from scripts.evaluation_transport import quality_eligible
    rows=[]
    for p in sorted((OUT/'stress').glob('*.json')):
        r=read(p)
        if not quality_eligible(r):
            continue
        result=r['result']
        structural=bool(result.get('citation_errors'))
        semantic=any(result.get(k,{}).get('checked_claim_ids') and result[k].get('supported') is False for k in ['evidence_verdict','safety_verdict'])
        rows.append({'case_id':r['id'],'guideline':r['id'].split('-')[0],'family':r['family'],
                     'unverified_released':1,'verified_released':int(result['status']=='supported_for_review'),
                     'structural_rejection':int(structural),'semantic_rejection':int(not structural and semantic),
                     'invalid_review':int(not structural and not semantic and result['status']!='supported_for_review')})
    table('fault_injection_per_case',rows)
    output=[]
    for g in ['NICE','AAP','WHO']:
        group=[r for r in rows if r['guideline']==g]
        if group:
            output.append({'guideline':g,'planned_n':12,'quality_n':len(group),
                'unverified_released':len(group),'verified_released':sum(r['verified_released'] for r in group),
                'structural_rejection':sum(r['structural_rejection'] for r in group),'semantic_rejection':sum(r['semantic_rejection'] for r in group),
                'invalid_review':sum(r['invalid_review'] for r in group),
                **ci([r['verified_released']-1 for r in group],[r['family'] for r in group])})
    table('fault_injection_summary',output)
    return output

def resolution_tables():
    from scripts.evaluation_transport import quality_eligible
    cases,_,protocol=validate()
    guideline={r['id']:r['guideline'] for r in read(OUT/'manifest.json')['cases']}
    pairs=[]
    for model in protocol['backbone_models']:
        folder=OUT/'backbones'/model.replace('/','_')
        for case in cases:
            paths=[folder/arm/f'{case["id"]}.json' for arm in ['no_repair','one_repair']]
            if not all(p.exists() for p in paths):
                continue
            before,after=[read(p) for p in paths]
            if not all(quality_eligible(r) for r in [before,after]):
                continue
            pairs.append({'model':model,'case_id':case['id'],'guideline':guideline[case['id']],'family':case['family'],
                'no_repair_released':int(before['result']['status']=='supported_for_review'),
                'one_repair_released':int(after['result']['status']=='supported_for_review'),
                'resolution_attempted':int(bool(after['result'].get('resolution_log'))),
                'revision_materialized':int(bool(after['result'].get('resolution_trace')) and after['result']['draft']!=before['result']['draft'])})
    table('resolution_per_case',pairs)
    summaries=[]
    for model in protocol['backbone_models']:
        for g in ['NICE','AAP','WHO']:
            group=[r for r in pairs if r['model']==model and r['guideline']==g]
            if group:
                summaries.append({'model':model,'guideline':g,'planned_n':protocol['guideline_counts'][g],
                    'paired_n':len(group),'no_repair_released':sum(r['no_repair_released'] for r in group),
                    'one_repair_released':sum(r['one_repair_released'] for r in group),
                    'resolution_attempts':sum(r['resolution_attempted'] for r in group),
                    **ci([r['one_repair_released']-r['no_repair_released'] for r in group],[r['family'] for r in group])})
    table('resolution_summary',summaries)
    return summaries

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--score-alignment',action='store_true')
    parser.add_argument('--score-saved',action='store_true')
    args=parser.parse_args()
    if args.score_alignment or args.score_saved:
        score_alignment(saved_only=args.score_saved)
    else:
        refresh_saved_judges()
    retrieval, retrieval_deltas=retrieval_tables()
    alignment, alignment_deltas=alignment_tables()
    faults=fault_tables()
    resolution=resolution_tables()
    old=read(ROOT/'output/research/rag_v2/summary.json')
    changes=[]
    for r in retrieval:
        legacy_nice=old['retrieval'][r['method']][r['metric']] if 'retrieval' in old else read(ROOT/'output/research/rag_v2/retrieval.json')['summary'][r['method']][r['metric']]
        old_value=legacy_nice if r['guideline']=='NICE' else None
        changes.append({'domain':'retrieval','guideline':r['guideline'],'metric':r['metric'],'method':r['method'],
                        'quoted_old_value':repr(old_value) if old_value is not None else 'not reported for this guideline',
                        'old_paper_display_value':f'{old_value:.4f}' if old_value is not None else 'not reported',
                        'legacy_NICE_reference_value':legacy_nice,
                        'new_value':r['mean'],'difference':r['mean']-old_value if old_value is not None else None,
                        'changed':old_value!=r['mean'],
                        'comparable_population':False,'note':'Old NICE n18; new guideline-specific cohorts and current frozen runtime'})
    arm_map={'without_verification':'without_verification','verified_all_cases':'with_verification_all_cases',
             'released_only':'with_verification_released_only','generated_only':'without_verification_generated_only'}
    for r in alignment:
        old_arm=old['arms'].get(arm_map[r['arm']],{}) if r['guideline']=='NICE' else {}
        old_value=old_arm.get('metrics',{}).get(r['metric'])
        changes.append({'domain':'alignment','guideline':r['guideline'],'metric':r['metric'],'method':r['arm'],
            'quoted_old_value':repr(old_value) if old_value is not None else 'not reported',
            'new_value':r['mean'],'difference':r['mean']-old_value if r['mean'] is not None and old_value is not None else None,
            'changed':r['mean']!=old_value,'comparable_population':False,
            'old_emission_coverage':old_arm.get('coverage'),'new_emission_coverage':r['coverage'],
            'new_emitted':r['emitted'],'new_quality_n':r['quality_n'],
            'note':'Historical NICE n18 versus source-stratified expanded cohort; conditional coverage definition also differs.'})
    if (TABLES/'judge_by_guideline.csv').exists():
        with (TABLES/'judge_by_guideline.csv').open(encoding='utf8') as f:current_judges=list(csv.DictReader(f))
        for r in current_judges:
            old_arm=old['arms'].get('without_verification' if r['arm']=='without_verification' else 'with_verification_released_only',{}) if r['guideline']=='NICE' else {}
            old_value=old_arm.get('judge_unsafe_claims') if r['metric']=='unsafe_claim_count' else old_arm.get('judge_means',{}).get(r['metric'])
            new_value=float(r['observed_sum']) if r['metric']=='unsafe_claim_count' else float(r['mean']) if r['mean'] else None
            changes.append({'domain':'judge','guideline':r['guideline'],'metric':r['metric'],'method':r['arm'],
                'quoted_old_value':repr(old_value) if old_value is not None else 'not reported for this guideline',
                'old_paper_display_value':str(int(old_value)) if old_value is not None and r['metric']=='unsafe_claim_count' else f'{old_value:.3f}' if old_value is not None else 'not reported',
                'new_value':new_value,'difference':new_value-old_value if new_value is not None and old_value is not None else None,
                'changed':old_value!=new_value,'comparable_population':False,
                'old_judge_n':old_arm.get('judge_n'),'new_judge_n':int(r['judge_n']),
                'note':'Dependent judge; source cohorts and selected release populations differ.'})
    for metric,old_value,new_value in [('benchmark_n',18,100),('guideline_count',1,3),('planned_faults',12,36),('NICE_index_chunks',132,132),('AAP_index_chunks',0,43),('WHO_index_chunks',0,141)]:
        changes.append({'domain':'design','guideline':'all','metric':metric,'quoted_old_value':repr(old_value),
                        'new_value':new_value,'difference':new_value-old_value,'changed':old_value!=new_value,
                        'comparable_population':False,'note':'User-requested design expansion'})
    table('old_vs_new',changes)
    complete_primary=(OUT/'per_case_metrics.json').exists() and len(read(OUT/'per_case_metrics.json'))==100
    complete_faults=len(faults)==3 and all(r['quality_n']==12 for r in faults)
    complete_backbones=len(resolution)==6 and all(r['paired_n']==r['planned_n'] for r in resolution)
    judge_files=sum((OUT/'judges'/f'{c["id"]}.json').exists() for c in read(OUT/'cases.json'))
    complete_judges=judge_files==100
    overall_complete=bool(complete_primary and complete_faults and complete_backbones and complete_judges)
    summary={'planned_n':100,'retrieval':retrieval,'retrieval_paired':retrieval_deltas,'alignment':alignment,
             'alignment_paired':alignment_deltas,'faults':faults,'resolution':resolution,
             'complete_primary_metrics':bool(complete_primary),'complete_faults':complete_faults,
             'complete_backbones':complete_backbones,'complete_judge_execution':complete_judges,
             'judge_files_completed':judge_files,'overall_complete':overall_complete,'bootstrap_resamples':B,'seed':SEED}
    save(OUT/'tables_summary.json',summary)
    lines=['# Expanded evaluation: 100 synthetic cases','', 'NICE 40; AAP 30; WHO 30. The original 18 cases remain unchanged. Results are engineering measurements; clinician adjudication is pending.', '',
           'All intervals use 2,000 bootstrap resamples, seed 31. Case intervals resample cases; family intervals resample all members of a scenario family together. Six authored families are too few for broad population inference.', '',
           '|Guideline|Method|Recall@4 (case 95% CI)|MRR@4 (case 95% CI)|','|---|---|---|---|']
    for g in ['NICE','AAP','WHO']:
        for method in ['lexical','dense','hybrid','hybrid_concepts']:
            x=[r for r in retrieval if r['guideline']==g and r['method']==method]
            def fmt(r):return f'{r["mean"]:.6f} [{r["case_low"]:.6f}, {r["case_high"]:.6f}]'
            lines.append(f'|{g}|{method}|{fmt(x[0])}|{fmt(x[1])}|')
    lines+=['','Full precision, family intervals and paired contrasts are in the CSV tables. Negative differences are retained.', '',
            f'Stage status: primary metrics {"complete" if complete_primary else "pending"}; fault tests {sum(r["quality_n"] for r in faults)}/36; judge executions {judge_files}/100; paired backbone/resolution executions {sum(r["paired_n"] for r in resolution)}/200.', '',
            'The full declared study is '+('complete.' if overall_complete else 'in progress. Missing/provider-failed work is not a quality result; no final manuscript claim is inferred from pending stages.'), '',
            'The identical initial draft forms both primary arms. Verification changes release/withholding, not the wording of released drafts. Released-only alignment must be read beside release coverage.', '',
            'WHO has a broader age/resource-setting scope. Its 0-72-hour subset is evaluated separately; absence of a WHO recommendation is not filled using NICE or AAP guidance. The technical graph is fixed concept expansion, not proof of causal reasoning or live Neo4j performance.', '',
            'The 114-case retrieval-only prototype and the WHO duplicate-index amendment remain archived. No RRF, k, encoder, concept mapping or generation prompt was tuned using the expanded results. Historical/current verifier source drift is logged in protocol.json.']
    def number(value):
        return 'NA' if value is None else f'{value:.3e}' if 0<abs(value)<.0001 else f'{value:.6f}'
    if alignment:
        lines+=['','## Primary paired release experiment','',
            '|Guideline|Arm|Emitted / quality N|Corpus BLEU-4|METEOR|ROUGE-L|DistilBERT F1|RoBERTa F1|',
            '|---|---|---:|---:|---:|---:|---:|---:|']
        for g in ['NICE','AAP','WHO']:
            for arm in ['without_verification','verified_all_cases','released_only','generated_only']:
                values={r['metric']:r for r in alignment if r['guideline']==g and r['arm']==arm}
                if not values:continue
                row=values['bert_f1']
                lines.append(f'|{g}|{arm}|{row["emitted"]}/{row["quality_n"]}|'+ '|'.join(number(values[k]['mean']) for k in ['corpus_bleu4','meteor','rougeL','bert_f1','roberta_f1'])+'|')
        lines+=['','All-case empty outputs affect corpus BLEU brevity as well as overlap. Conditional alignment does not establish clinical correctness or a rewriting benefit.', '',
            '|Guideline|Paired N|Released / N|DistilBERT F1 difference|Case 95% CI|Family 95% CI|',
            '|---|---:|---:|---:|---|---|']
        for r in alignment_deltas:
            if r['metric']=='bert_f1':
                lines.append(f'|{r["guideline"]}|{r["n"]}|{r["released"]}/{r["n"]}|{number(r["mean"])}|[{number(r["case_low"])}, {number(r["case_high"])}]|[{number(r["family_low"])}, {number(r["family_high"])}]|')
        judge_path=TABLES/'judge_by_guideline.csv'
        if judge_path.exists():
            with judge_path.open(encoding='utf8') as f:judge_rows=list(csv.DictReader(f))
            lines+=['','## Blinded model-judge proxies','',
                '|Guideline|Arm|Judged / quality N|Grounding|Patient fidelity|Actionability|Observed unsafe claims|',
                '|---|---|---:|---:|---:|---:|---:|']
            for g in ['NICE','AAP','WHO']:
                for arm in ['without_verification','with_verification']:
                    selected={r['metric']:r for r in judge_rows if r['guideline']==g and r['arm']==arm}
                    if not selected:continue
                    row=selected['grounding']
                    values=[number(float(selected[k]['mean'])) if selected[k]['mean'] else 'NA' for k in ['grounding','patient_fidelity','actionability']]
                    lines.append(f'|{g}|{arm}|{row["judge_n"]}/{row["quality_n"]}|'+ '|'.join(values)+f'|{selected["unsafe_claim_count"]["observed_sum"]}|')
            lines+=['','The judge shares the generator/auditor model. Released-only means are selection comparisons, not evidence that verification improved the same text. Ratings are not measured clinician usability.']
    lines+=['','## Fault challenge','', '|Guideline|Completed / planned|Structural reject|Semantic reject|Invalid review|Verified emitted|', '|---|---:|---:|---:|---:|---:|']
    for r in faults:
        lines.append(f'|{r["guideline"]}|{r["quality_n"]}/12|{r["structural_rejection"]}|{r["semantic_rejection"]}|{r["invalid_review"]}|{r["verified_released"]}|')
    lines+=['','## Additional backbones and bounded resolution','',
        ('Completed counts.' if complete_backbones else 'Provisional counts: this stage is still running; no final manuscript claim is made.'), '',
        '|Model|Guideline|Paired / planned|Baseline releases|One-repair releases|Attempts|Release-fraction difference|', '|---|---|---:|---:|---:|---:|---:|']
    for r in resolution:
        lines.append(f'|{r["model"]}|{r["guideline"]}|{r["paired_n"]}/{r["planned_n"]}|{r["no_repair_released"]}|{r["one_repair_released"]}|{r["resolution_attempts"]}|{number(r["mean"])}|')
    lines+=['','Full case/family intervals, original-18 controls and quoted historical values are in the CSV tables. The clinician bundle contains unfilled adjudication fields; no clinician acceptance is inferred.']
    (OUT/'results_summary.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print({'retrieval_rows':len(retrieval),'alignment_rows':len(alignment),'fault_guidelines':len(faults),'resolution_groups':len(resolution)})

if __name__=='__main__':
    main()
