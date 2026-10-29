"""Prepare lossless research export inputs; pending cases never masquerade as plans."""
import hashlib,json,csv,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'output/research/rag_development';RUN=BASE/'care_plan_100_v22'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write-csv',action='store_true');args=parser.parse_args()
    cases=json.loads((ROOT/'output/research/expanded100/cases.json').read_text(encoding='utf8'));corpus={c['chunk_id']:c for c in json.loads((BASE/'recommendation_units/corpus.json').read_text(encoding='utf8'))['chunks']}
    rows=[];counts={};complete=0
    for c in cases:
        path=RUN/'runs'/f'{c["id"]}.json';d=json.loads(path.read_text(encoding='utf8'))if path.exists()else None;r=d['result']if d else {}
        gold=[{'chunk_id':g,'full_text':corpus[g].get('raw_text',corpus[g]['text']),'source':corpus[g]['source'],'version':corpus[g]['version'],'sha256':hashlib.sha256(corpus[g].get('raw_text',corpus[g]['text']).encode()).hexdigest(),'clinical_review_status':corpus[g].get('clinical_review_status','pending')}for g in c['gold_chunk_ids']]
        status=r.get('plan_release_status','pending_execution');counts[status]=counts.get(status,0)+1
        if d:complete+=1
        row={'case_id':c['id'],'scenario_family':c['family'],'guideline':d['guideline']if d else c['gold_chunk_ids'][0].split('-')[0],'execution_status':d.get('execution_classification','completed')if d else 'pending','all_case_details_json':json.dumps(c,ensure_ascii=False),'case_details_text':c['query']+'\n\nPatient details:\n'+json.dumps(c['patient'],ensure_ascii=False,indent=2)+'\n\nLongitudinal history:\n'+json.dumps(c['history'],ensure_ascii=False,indent=2),'patient_json':json.dumps(c['patient'],ensure_ascii=False),'longitudinal_history_json':json.dumps(c['history'],ensure_ascii=False),'question':c['query'],'gold_target_ids_json':json.dumps(c['gold_chunk_ids']),'gold_target_passages_text':'\n\n'.join(g['chunk_id']+' | '+g['source']+' | '+g['version']+'\n'+g['full_text']for g in gold),'gold_target_passages_json':json.dumps(gold,ensure_ascii=False),'generated_care_plan':'\n\n'.join(s['id']+' '+s['title']+'\n'+'\n'.join(s['items'])for s in r.get('plan_sections',[])),'uncertainty_json':json.dumps(r.get('uncertainty',{}),ensure_ascii=False),'caregiver_note_json':json.dumps(r.get('caregiver_note',{}),ensure_ascii=False),'plan_sections_json':json.dumps(r.get('plan_sections',[]),ensure_ascii=False),'patient_criteria_met_not_met_unknown_json':json.dumps(r.get('patient_application',{}),ensure_ascii=False),'retrieved_evidence_json':json.dumps(d['packet']['evidence']if d else [],ensure_ascii=False),'release_status':status,'reference_completeness_passed':str(r.get('completeness',{}).get('passed',False)),'missing_core_sections':'; '.join(sorted(set(r.get('completeness',{}).get('required_sections',[]))-set(r.get('completeness',{}).get('supported_sections',[])))),'auditor_rejection_reasons_json':json.dumps({k:r.get(k,{}).get('reasons',[])for k in ['evidence_verdict','safety_verdict']},ensure_ascii=False),'verifier_errors_json':json.dumps({k:r[k].get('error_code')for k in ['evidence_verdict','safety_verdict']if k in r and r[k].get('error_code')}),'clinical_validation':'not performed','output_kind':'patient-specific evidence review; not autonomous treatment orders','run_sha256':hashlib.sha256(path.read_bytes()).hexdigest()if d else ''}
        rows.append(row)
    out=ROOT/'output/clinician-review/case_exports';out.mkdir(parents=True,exist_ok=True)
    # Research intermediate; the delivery CSV is authored/round-tripped through artifact-tool.
    inputs=[{'name':'neoguard_100_case_rerun_v22','headers':list(rows[0]),'rows':[list(r.values())for r in rows]}]
    finished=[r for r in rows if r['execution_status']!='pending']
    if finished and len(finished)<100:inputs.append({'name':'neoguard_completed_case_plans_v22','headers':list(rows[0]),'rows':[list(r.values())for r in finished]})
    temp=ROOT/'tmp/case-csv/rerun_inputs.json';temp.parent.mkdir(parents=True,exist_ok=True);temp.write_text(json.dumps(inputs,ensure_ascii=False),encoding='utf8')
    if args.write_csv:
        for item in inputs:
            with (out/(item['name']+'.csv')).open('w',encoding='utf-8-sig',newline='')as f:
                writer=csv.writer(f,quoting=csv.QUOTE_ALL);writer.writerow(item['headers']);writer.writerows(item['rows'])
    summary={'planned_cases':100,'completed_cases':complete,'pending_cases':100-complete,'release_status_counts':counts,'clinical_reviews':0,'clinical_usability_established':False,'development_population':'100 exposed synthetic cases; no independent clinical validation','export_includes_pending':complete<100}
    (RUN/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    print(json.dumps(summary))
if __name__=='__main__':main()
