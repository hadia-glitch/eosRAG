"""Recompute the seven protocol CSVs from frozen sources and saved fresh judgments."""
import ast,csv,json,math,re,unicodedata
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/research/phase1_pilot'
ARMS={'dense_only':'dense','sparse_only':'sparse','vector':'vector','graph':'graph','hybrid':'hybrid',
      'dense_only_multiagent':'dense_ma','hybrid_multiagent':'hybrid_ma'}
NA='NOT EVALUATED'
HEADERS={
'01_pilot_exact_retrieval.csv':'case_id,guideline,arm,exact_mrr_at10,exact_ndcg_at10,anchor_grounding_recall',
'02_pilot_llm_chunk_judgments.csv':'case_id,guideline,arm,rank,chunk_id,relevance_grade,guideline_aligned,scenario_applicable,clinically_useful,rationale',
'03_pilot_semantic_summary.csv':'arm,cases_evaluated,utility_precision_at10,semantic_mrr_at10,semantic_ndcg_at10',
'04_pilot_clinical_usability.csv':'case_id,guideline,arm,faithfulness,citation_correctness,citation_completeness,clinical_correctness,clinical_completeness,clinical_utility,safety,unsupported_claims,contradictions,critical_omissions',
'05_pilot_generation.csv':'case_id,guideline,arm,bleu,meteor,bertscore_f1,anchor_grounding_recall',
'06_pilot_multiagent.csv':'case_id,guideline,arm,factcheck_verified,confidence,resolution_steps,regimen_incomplete,ungrounded_dose,unsupported_claims',
'07_pilot_consolidated_results.csv':'evaluation_tier,metric,dense,sparse,vector,graph,hybrid,dense_ma,hybrid_ma,n_cases,interpretation'}

def norm(t):return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',t).casefold()))
def anchor_recall(anchors,text):
    anchors={norm(a) for a in anchors if norm(a)};text=' '+norm(text)+' '
    return sum(' '+a+' ' in text for a in anchors)/len(anchors) if anchors else NA
def dcg(grades):return sum((2**g-1)/math.log2(i+2) for i,g in enumerate(grades[:10]))
def mrr(grades,cut=1):return next((1/(i+1) for i,g in enumerate(grades[:10]) if g>=cut),0.)
def emit(name,rs):
    path=OUT/name;temporary=path.with_suffix('.csv.tmp')
    with temporary.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=HEADERS[name].split(','),extrasaction='raise');w.writeheader();w.writerows(rs)
    temporary.replace(path)
def boolean(v):return str(v).lower()=='true'

def main():
    x=json.loads((OUT/'inputs.json').read_text());cases={c['case_id']:c for c in x['cases']};corpus=x['corpus']
    exact=[];chunks=[];semantic=[];usability=[];generation=[];multiagent=[];judges={};plans={};stages={};consistency=[]
    for path in (OUT/'judges').glob('*.json'):
        j=json.loads(path.read_text())
        if not j.get('completed'):continue
        if j['kind']=='chunks':
            for r in j['result']['judgments']:
                cid=j['case_id'];chunk=j['mapping'][r['passage']]
                if r['relevance_grade']>=2 and not (r['guideline_aligned'] and r['scenario_applicable']):consistency.append({'case_id':cid,'chunk_id':chunk,'judgment':r})
                if r['clinically_useful']!=(r['relevance_grade']>=2):consistency.append({'case_id':cid,'chunk_id':chunk,'type':'grade_usefulness_disagreement','judgment':r})
                key=(cid,chunk)
                if key in judges:raise RuntimeError('Duplicate fresh case/chunk judgment: '+str(key))
                judges[key]=r
        elif j.get('rubric_version')==4:stages.setdefault((j['case_id'],j['mapping']['arm']),{})[j['evaluation_stage']]=j['result']
    for key,parts in stages.items():
        if set(parts)=={'grounding','clinical'}:
            plans[key]={**parts['clinical'],**parts['grounding'],
                'contradictions':parts['grounding']['contradictions']+parts['clinical']['contradictions']}
    for row in x['retrieval']:
        c=cases[row['case_id']];ids=ast.literal_eval(row['retrieved_chunk_ids'])[:10];gold=set(c['gold_chunk_ids'])
        hits=[];seen=set()
        for i in ids:hits.append(int(i in gold and i not in seen));seen.add(i)
        ideal=dcg([1]*min(10,len(gold)))
        exact.append(dict(case_id=c['case_id'],guideline=c['active_guideline'],arm=ARMS[row['arm']],
            exact_mrr_at10=mrr(hits),exact_ndcg_at10=dcg(hits)/ideal if ideal else NA,
            anchor_grounding_recall=anchor_recall(c['anchor_phrases'],'\n'.join(corpus[i]['chunk_text'] for i in ids))))
        for rank,i in enumerate(ids,1):
            j=judges.get((c['case_id'],i))
            if j:chunks.append(dict(case_id=c['case_id'],guideline=c['active_guideline'],arm=ARMS[row['arm']],rank=rank,chunk_id=i,
                relevance_grade=j['relevance_grade'],guideline_aligned=j['guideline_aligned'],scenario_applicable=j['scenario_applicable'],
                clinically_useful=j['relevance_grade']>=2,rationale=j['rationale']))
    for cid,c in cases.items():
        rows=[r for r in x['retrieval'] if r['case_id']==cid]
        union={i for r in rows for i in ast.literal_eval(r['retrieved_chunk_ids'])[:10]}
        if not all((cid,i) in judges for i in union):continue
        ideal=dcg(sorted([judges[(cid,i)]['relevance_grade'] for i in union],reverse=True))
        for row in rows:
            ids=ast.literal_eval(row['retrieved_chunk_ids'])[:10];seen=set();grades=[]
            for i in ids:grades.append(judges[(cid,i)]['relevance_grade'] if i not in seen else 0);seen.add(i)
            semantic.append(dict(case_id=cid,guideline=c['active_guideline'],arm=ARMS[row['arm']],
                utility_precision_at10=sum(g>=2 for g in grades)/10,semantic_mrr_at10=mrr(grades,2),semantic_ndcg_at10=dcg(grades)/ideal if ideal else 0.))
    summaries=[]
    for arm in ['dense','sparse','vector','graph','hybrid']:
        rs=[r for r in semantic if r['arm']==arm]
        summaries.append({'arm':arm,'cases_evaluated':len(rs),**{k:mean(r[k] for r in rs) if rs else NA for k in ['utility_precision_at10','semantic_mrr_at10','semantic_ndcg_at10']}})
    metric_path=OUT/'generation_metrics.json';gmetrics=json.loads(metric_path.read_text()).get('records',[]) if metric_path.exists() else []
    for row in x['generation']:
        c=cases[row['case_id']];j=plans.get((row['case_id'],row['arm']))
        scores=['faithfulness','citation_correctness','citation_completeness','clinical_correctness','clinical_completeness','clinical_utility','safety']
        usability.append({'case_id':c['case_id'],'guideline':c['active_guideline'],'arm':ARMS[row['arm']],
            **{k:j[k] if j else NA for k in scores},**{k:json.dumps(j[k],ensure_ascii=True) if j else NA for k in ['unsupported_claims','contradictions','critical_omissions']}})
        m=next((r for r in gmetrics if r['case_id']==c['case_id'] and r['arm']==row['arm']),None)
        generation.append({'case_id':c['case_id'],'guideline':c['active_guideline'],'arm':ARMS[row['arm']],
            **{k:m.get(k,NA) if m else NA for k in ['bleu','meteor','bertscore_f1']},
            'anchor_grounding_recall':anchor_recall(c['anchor_phrases'],row['generated_text'])})
    for row in x['multiagent']:
        c=cases[row['case_id']];j=plans.get((row['case_id'],row['arm']))
        multiagent.append({'case_id':c['case_id'],'guideline':c['active_guideline'],'arm':ARMS[row['arm']],
            'factcheck_verified':boolean(row['fact_check_verified']) if row['fact_check_verified'] else NA,
            'confidence':float(row['fact_check_confidence']) if row['fact_check_confidence'] else NA,
            'resolution_steps':int(row['n_resolution_steps']) if row['n_resolution_steps'] else NA,
            'regimen_incomplete':j['regimen_incomplete'] if j else NA,'ungrounded_dose':j['ungrounded_dose'] if j else NA,
            'unsupported_claims':json.dumps(j['unsupported_claims'],ensure_ascii=True) if j else NA})
    consolidated=[]
    def add(tier,metric,records,key,interpretation,transform=lambda v:v):
        values={}
        for arm in ARMS.values():
            rs=[transform(r[key]) for r in records if r['arm']==arm and r.get(key)!=NA]
            values[arm]=mean(rs) if rs else NA
        counts=[sum(r['arm']==arm and r.get(key)!=NA for r in records) for arm in ARMS.values()]
        consolidated.append({'evaluation_tier':tier,'metric':metric,**values,'n_cases':max(counts,default=0),'interpretation':interpretation})
    for k in ['exact_mrr_at10','exact_ndcg_at10','anchor_grounding_recall']:add('Tier 1',k,exact,k,'Frozen 100-case gold; top-10 only; no gold repair. Ten metadata-selected paired cases.')
    for k in ['utility_precision_at10','semantic_mrr_at10','semantic_ndcg_at10']:add('Tier 2',k,semantic,k,'Fresh arm-blinded LLM judgments; only cases with every union passage judged; development pilot, not clinician validation.')
    for k in ['faithfulness','citation_correctness','citation_completeness','clinical_correctness','clinical_completeness','clinical_utility','safety']:add('Tier 3',k,usability,k,'LLM-based clinical usability assessment - not clinician validation. 1-5 scale.')
    for k in ['bleu','meteor','bertscore_f1','anchor_grounding_recall']:add('Generation',k,generation,k,'Freshly recomputed vs frozen template reference; lexical/semantic similarity does not establish clinical correctness.')
    for k in ['factcheck_verified','confidence','resolution_steps']:add('Multi-agent',k,multiagent,k,'Reported historical trace field; confidence is not calibrated clinical confidence; independent generations are not a controlled agent ablation.')
    for k in ['regimen_incomplete','ungrounded_dose']:add('Multi-agent',k,multiagent,k,'Fresh LLM source/case assessment of saved MA output, not historical safety flags.')
    add('Multi-agent','unsupported_claim_rate',multiagent,'unsupported_claims','Fraction of plans with >=1 fresh-judge unsupported claim.',lambda v:bool(json.loads(v)))
    records=[exact,chunks,summaries,usability,generation,multiagent,consolidated]
    for name,rs in zip(HEADERS,records):emit(name,rs)
    progress={'selected_cases':len(cases),'fresh_unique_chunk_judgments':len(judges),'required_unique_chunk_judgments':len({(r['case_id'],i) for r in x['retrieval'] for i in ast.literal_eval(r['retrieved_chunk_ids'])[:10]}),
        'complete_semantic_cases':len(semantic)//5,'fresh_plan_judgments':len(plans),'required_plan_judgments':40,
        'fresh_plan_stage_judgments':sum(len(v) for v in stages.values()),'required_plan_stage_judgments':80,
        'generation_metric_pairs':len(gmetrics),'judge_relevance_applicability_disagreements':consistency,
        'semantic_per_case':semantic,'complete':len(semantic)==50 and len(plans)==40 and len(gmetrics)==20}
    (OUT/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    print(json.dumps({k:v for k,v in progress.items() if k not in ['semantic_per_case','judge_relevance_applicability_disagreements']}))

if __name__=='__main__':main()
