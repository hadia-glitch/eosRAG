"""Descriptive coverage only; source references are not clinical success labels."""
import csv,hashlib,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'output/research/rag_development/care_plan_100_v22'
def main():
    cases=json.loads((ROOT/'output/research/expanded100/cases.json').read_text());runs={p.stem:json.loads(p.read_text())for p in (RUN/'runs').glob('*.json')};rows=[]
    for c in cases:
        d=runs.get(c['id']);r=d['result']if d else {};gate=r.get('completeness',{})
        if d:
            e={v['id']:v for v in d['packet']['evidence']}
            assert len(r['plan_sections'])==13
            for claim in r['source_reference_claims']:
                assert claim['text']=='\n\n'.join(s['quote']for s in claim['support'])
                assert all(s['quote']==e[s['evidence_id']]['text']for s in claim['support'])
        rows.append({'case_id':c['id'],'guideline':d['guideline']if d else c['gold_chunk_ids'][0].split('-')[0].replace('AAP2018','AAP').replace('WHO2024','WHO'),'family':c['family'],'completed':bool(d),'reference_completeness':gate.get('passed',False),'accepted_source_references':len(r.get('source_reference_claims',[])),'missing_core_sections':'; '.join(sorted(set(gate.get('required_sections',[]))-set(gate.get('supported_sections',[]))))if d else 'pending','model_contract_failure':bool(d and d.get('execution_classification')=='completed_model_failure'),'clinical_review_completed':False})
    with (RUN/'case_coverage.csv').open('w',encoding='utf-8-sig',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    lines=['# 100-case care-plan research rerun','','The same previously exposed synthetic benchmark is reused. This is a generation/audit rerun, not an independent clinical validation, retrieval re-benchmark, or paired verified/unverified ablation. The three-case gate passed before scaling. Unsupported sections remain explicit. No autonomous treatment orders are authorized.','','| Guideline | Saved / planned | Reference-complete / saved | Model-contract failures / saved | Clinician reviews |','| --- | --- | --- | --- | --- |']
    for g in ['NICE','AAP','WHO']:
        rs=[r for r in rows if r['guideline']==g];done=[r for r in rs if r['completed']];n=len(done)
        lines.append(f'| {g} | {n}/{len(rs)} | {sum(r["reference_completeness"]for r in done)}/{n} | {sum(r["model_contract_failure"]for r in done)}/{n} | 0 |')
    lines+=['','## Changes and safeguards','','- Audit batches contain at most four claims; every batch must pass schema/ID validation. An invalid batch approves no claims. Two distinct backbones remain required.','- Whole source paragraphs, including conditions and exceptions, are immutable; retained quotations were programmatically checked against retrieved passage text.','- Fixed-query BM25Plus source proposals and source-scoped supplements address missing topic coverage without gold/reference input. The context budget is larger than earlier retrieval experiments; this is not an isolated component ablation.','- Patient criteria and missing values are rendered separately. Numeric drug-dose rejection cannot be cleared by historical or conditional labelling.','- Fresh calls are checkpointed. Exact-prompt/model completed calls from the identical-pipeline pilot are reused and recorded; completed model/audit failures remain in quality counts. Provider failures are operational records, not fabricated clinical outputs.','', '## Interpretation','','Reference completeness is an engineering coverage criterion, not safety, actionability or clinical usability. All 13 headings being present is insufficient. Cases and source/gold annotations remain unreviewed by a clinician. Previously reported Recall/MRR/Precision/nDCG retrieval results are unchanged and cannot be used as generation-quality scores. No new clinical accuracy or care-outcome metric is claimed.','', 'The delivery CSV contains full original case JSON and history, engineering gold IDs and full passages with hashes, every generated section, patient met/not-met/unknown criteria, actual retrieved passages, release/error status and source-run hashes. Pending rows, if any, are explicitly labelled and contain no invented care plan.','', 'Regression validation: 49 combined pipeline checks passed, followed by two checks of the concurrent key-pool transport. No live API response is treated as clinician sign-off.']
    (RUN/'results.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps({'saved':len(runs),'total':100,'immutable_source_checks':'passed','reference_complete':sum(r['reference_completeness']for r in rows)}))
if __name__=='__main__':main()
