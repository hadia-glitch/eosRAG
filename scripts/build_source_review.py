"""Export complete case/source/state records without assigning clinical ratings."""
import argparse,csv,hashlib,html,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',default='15');parser.add_argument('--run-dir');parser.add_argument('--output-name');args=parser.parse_args()
    base=ROOT/'output/research/rag_development';run=ROOT/args.run_dir if args.run_dir else base/f'patient_care_plan_v{args.version}'
    out=ROOT/'output/clinician-review'/(args.output_name or f'neoguard-source-review-v{args.version}');out.mkdir(parents=True,exist_ok=True)
    cases={c['id']:c for c in json.loads((ROOT/'output/research/expanded100/cases.json').read_text(encoding='utf8'))}
    corpus={c['chunk_id']:c for c in json.loads((base/'recommendation_units/corpus.json').read_text(encoding='utf8'))['chunks']}
    rows=[];ratings=[];hashes={};esc=html.escape
    pages=['<!doctype html><meta charset="utf-8"><title>Patient-specific source review</title><style>body{max-width:1050px;margin:30px auto;font:16px/1.6 system-ui;color:#19374b}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6fa;padding:15px}article{border-top:2px solid #abc;margin-top:30px}li{margin:12px 0}</style><h1>Care-plan development source review</h1><p>Synthetic cases. This is a source-reference candidate, not a clinically validated care plan or patient treatment order. No clinician ratings have been assigned. Unsupported sections remain visible.</p>']
    for path in sorted((run/'runs').glob('*.json')):
        d=json.loads(path.read_text(encoding='utf8'));r=d['result'];case=cases[d['id']]
        gold=[corpus[g] for g in case['gold_chunk_ids']] # Fail loudly on missing annotation.
        context={'case':case,'recorded_patient':d['packet']['patient'],'history':d['packet'].get('history',[])}
        plan='\n\n'.join(s['id']+' '+s['title']+'\n'+'\n'.join(s['items']) for s in r['plan_sections'])
        row={'case_id':d['id'],'guideline':d['guideline'],'case_all_details_json':json.dumps(context,ensure_ascii=False),'gold_ids_json':json.dumps(case['gold_chunk_ids']),'gold_passages_json':json.dumps(gold,ensure_ascii=False),'patient_application_json':json.dumps(r['patient_application'],ensure_ascii=False),'generated_plan_text':plan,'retrieved_passages_json':json.dumps(d['packet']['evidence'],ensure_ascii=False),'engineering_completeness_passed':r['completeness']['passed'],'clinical_validation':'not performed','output_kind':'immutable source reference review; not patient orders'}
        rows.append(row);hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        ratings.append({'case_id':d['id'],'patient_fit_1_to_5':'','source_fidelity_1_to_5':'','actionability_1_to_5':'','unsafe_or_missing_actions':'','wrong_scope_category_or_exception':'','required_corrections':'','reviewer':'','date':''})
        pages.append('<article><h2>'+esc(d['id'])+'</h2><h3>Complete case and history</h3><pre>'+esc(json.dumps(context,indent=2,ensure_ascii=False))+'</pre><h3>Criterion states: met / not met / unknown</h3><pre>'+esc(json.dumps(r['patient_application'],indent=2,ensure_ascii=False))+'</pre>')
        for s in r['plan_sections']:pages.append('<h3>'+esc(s['id']+' '+s['title'])+'</h3><ul>'+''.join('<li>'+esc(i)+'</li>' for i in s['items'])+'</ul>')
        pages.append('<h3>Full retrieved passages</h3><pre>'+esc(json.dumps(d['packet']['evidence'],indent=2,ensure_ascii=False))+'</pre><h3>Engineering gold passages (not clinician adjudicated)</h3><pre>'+esc(json.dumps(gold,indent=2,ensure_ascii=False))+'</pre></article>')
    if not rows:raise ValueError('No completed cases; refusing empty review export')
    for name,data in [('cases_gold_and_plans.csv',rows),('clinician_ratings.csv',ratings)]:
        with (out/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    (out/'review.html').write_text('\n'.join(pages),encoding='utf8')
    (out/'README.md').write_text('Open review.html and fill clinician_ratings.csv. All cases are synthetic. All 13 headings are shown, including unsupported sections; heading presence is not completeness or clinical usefulness. The CSV includes all case details, full engineering gold passages, immutable retrieved source references and patient criterion states. Gold annotations and clinical source approval remain unreviewed. No quality scores or clinician approval are implied. This is an exposed development sample, not an independent final evaluation.\n',encoding='utf8')
    manifest={'version':args.version,'completed_cases':len(rows),'clinical_reviews':0,'source_run_sha256':hashes,'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()and p.name!='manifest.json'}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    target=out.with_suffix('.zip')
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED)as z:
        for p in sorted(out.iterdir()):
            if p.is_file():z.write(p,p.name)
    with zipfile.ZipFile(target)as z:
        assert z.testzip()is None
        assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in manifest['files_sha256'].items())
    print(json.dumps({'bundle':str(target),'cases':len(rows),'complete_reference_reviews':sum(r['engineering_completeness_passed']for r in rows)}))
if __name__=='__main__':main()
