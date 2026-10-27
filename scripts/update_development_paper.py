"""Append measured development results; preserve the frozen study's tables."""
import csv
import difflib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'output/research/rag_development'
PAPER=ROOT/'docs/research/manuscript.md'


def read_csv(path):return list(csv.DictReader(path.open(encoding='utf8')))
def n(v):return f'{float(v):.4f}'
def interval(row,kind):return '['+n(row[kind+'_low'])+', '+n(row[kind+'_high'])+']'


def main():
    original=PAPER.read_text(encoding='utf8')
    snapshot=DATA/'manuscript_before_development.md'
    if not snapshot.exists():snapshot.write_text(original,encoding='utf8')
    facet=read_csv(DATA/'faceted/intervals.csv');listwise=read_csv(DATA/'listwise/intervals.csv')
    consensus=read_csv(DATA/'consensus/intervals.csv')
    differences=read_csv(DATA/'paper_retrieval_differences.csv')
    graph=read_csv(DATA/'faceted/paired_differences.csv')
    summary=json.loads((DATA/'listwise/summary.json').read_text())
    if not summary['complete']:raise ValueError('No incomplete development results in the paper')
    def row(rows,g,m,k,metric):return next(r for r in rows if (r['guideline'],r['method'],int(r['depth']),r['metric'])==(g,m,k,metric))
    lines=['## 13. Subsequent retrieval development and readiness boundary','',
        'This section is a post-hoc development extension on the same 100 previously examined synthetic cases, '
        'not a final evaluation or an untouched test. The original Sections 6-7 and their results remain a frozen '
        'historical study. No proposed gold identifier or engineering reference answer enters query planning, '
        'candidate retrieval, cross-encoder scoring or language-model passage ranking. Source and case '
        'adjudication remain pending.','',
        '### 13.1 Index structure, medical encoders and question coverage','',
        'Source headings and explicit age, gestation and care-setting limits are applied before retrieval. '
        'Seventeen explicitly late-only NICE passages are excluded in the logged structural index amendment. '
        'The remaining source index contains 299 passages. Publisher structure separates normative guidance '
        'from research background, leaving 115 NICE, 30 AAP and 16 WHO passages in the guidance lane; background '
        'remains separately available. This pool reduction is an engineering intervention and contributes '
        'to comparisons with the original index. The small WHO pool makes high-depth recall easier.','',
        'The NCBI MedCPT query, article and cross encoders are evaluated with frozen weights [16], alongside '
        'MiniLM/MS-MARCO controls. Medical pretraining does not establish clinical validity. Medical synonym '
        'expansion, RRF offset 60, overlapping cross-encoder windows (180 words, 40-word overlap), '
        'multi-question planning and bounded MMR are retained in logged ablations. MMR diversity 0.15 '
        'operates within the top twice-the-return-budget candidate set; a regression test demonstrates a '
        'near-duplicate neighbour swap. The earlier 0.1 ordinal weighting could be inert at four passages, '
        'so merely enabling that earlier option did not establish a diversity benefit. All five faceted '
        'methods and depths 1, 2, 4, 6, 8 and 12 remain in the result CSVs.','',
        'The planner produces 24 unique source/question requests. The known EOS system age scope is '
        'recognized in a logged offline validation amendment; 23 plans pass and one retains the original '
        'question. A second, bounded listwise stage receives the original focused question and up to '
        '24 full candidate passages formed by fixed fusion of four upstream rankings. It returns only '
        'existing identifiers, with at most eight passages; missing, duplicate or invented identifiers '
        'fail validation. No source text is rewritten. Identical question/candidate requests are cached '
        'exactly, so the case count does not equal the number of independent model requests.','',
        '### 13.2 Measured retrieval changes and negative results','',
        'Table 20. Development retrieval at four passages, with complete source populations. Precision '
        'remains conventional and is not ceiling-normalized. All case and family intervals, nDCG, F1 '
        'and evidence-word budgets are available in the corresponding CSV files.','',
        '| Source | Method | Complete / N | Recall@4 | Case 95% CI | Family 95% CI | MRR@4 | Precision@4 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for g,total in [('NICE',40),('AAP',30),('WHO',30)]:
        for label,rows,m in [('Medical faceted',facet,'medical_faceted'),('Bounded listwise',listwise,'listwise'),
                             ('RRF consensus',consensus,'consensus')]:
            r=row(rows,g,m,4,'recall');mr=row(rows,g,m,4,'mrr');p=row(rows,g,m,4,'precision')
            lines.append(f'| {g} | {label} | {total}/{total} | {n(r["mean"])} | {interval(r,"case")} | {interval(r,"family")} | {n(mr["mean"])} | {n(p["mean"])} |')
    lines+=['','Table 21. Medical faceted minus original frozen hybrid retrieval. Old paper values are '
        'quoted explicitly. These are combined index/model/query changes, not isolated causal component effects.','',
        '| Source | Metric | Old paper value | Development value | Paired change | Case 95% CI | Family 95% CI |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for r in differences:
        lines.append(f'| {r["guideline"]} | {r["metric"]} | {n(r["old_paper_value"])} | {n(r["new_value"])} | {n(r["mean"])} | {interval(r,"case")} | {interval(r,"family")} |')
    lines+=['','Recall@4 is higher in this development benchmark for all three sources. Both paired '
        'interval types exclude zero for those recall changes. The MRR differences for NICE and AAP '
        'do not exclude zero under scenario-family resampling, so a general superiority claim is unsupported. '
        'Bootstrap intervals use 2,000 resamples and seed 31; only six scenario families and repeated templates '
        'limit independence.','',
        'The listwise-only intervention lowers WHO recall and can produce an empty evidence selection '
        'for a question about a source limitation. It is therefore not adopted as an evidence-availability '
        'gate. A subsequent fixed RRF60 consensus treats its output as one relevance vote alongside '
        'the upstream ranking; an empty list contributes no vote. The consensus preserves reviewed '
        'candidate evidence for downstream assessment without declaring that it supports a treatment '
        'claim. Its negative and positive paired changes remain in separate CSVs; no new API calls '
        'are needed for this saved-request development regression.','',
        'Table 22. Explicit-reference graph variant minus medical faceted retrieval at four passages. '
        'Negative effects are retained.','',
        '| Source | Recall difference | Case 95% CI | Family 95% CI |',
        '| --- | --- | --- | --- |']
    for g in ['NICE','AAP','WHO']:
        r=next(r for r in graph if r['guideline']==g and r['contrast']=='medical_faceted_graph minus medical_faceted' and r['depth']=='4' and r['metric']=='recall')
        lines.append(f'| {g} | {n(r["mean"])} | {interval(r,"case")} | {interval(r,"family")} |')
    lines+=['','Graph candidate expansion does not improve the four-passage recall estimate in these '
        'three cohorts. A separate typed source-context graph links recommendations to exact definition '
        'sentences in the same publisher section. Every definition retains its parent passage, offsets '
        'and text/source hashes; engineering extraction is not clinical approval. Such context is an '
        'additional, explicitly counted evidence budget, not a hidden top-four slot. Its effect on '
        'answer quality is unmeasured. No live Neo4j deployment benefit is claimed from this offline graph.','',
        'Increasing the return budget can recover more annotated passages while lowering the precision '
        'ceiling and increasing context length; it does not turn Recall@8 into Recall@4. The fixed gold '
        'sets contain only two or three passages per case, so the conventional Precision@4 ceilings in '
        'Table 5a remain binding. Incomplete relevance annotation may also mark other useful evidence '
        'as irrelevant, but that possibility requires blinded clinician adjudication rather than '
        'a retrospective label change. Reference-alignment scores have no comparable demonstrated '
        'task-specific numeric ceiling; weak text alignment cannot be dismissed as an inevitable ceiling.','',
        '### 13.3 Application changes, clinical review and evaluation hold','',
        'The active application now passes the recorded care setting to RAG separately from ML predictors. '
        'The explicit positive or negative culture result selected in the Flutter form is also preserved; '
        'pending or unrecorded results remain unknown. '
        'The API distinguishes culture status, culture-incubation time and antibiotic-exposure time; '
        'patient age cannot substitute for either treatment clock. Passage-level scope is enforced in '
        'addition to document approval. Hospital-only eligibility and cloud-processing authorization '
        'are checked before retrieval, and the exact clinical task reaches both auditors. Missing '
        'eligibility, audit dissent and incomplete evidence remain explicit.','',
        'The medical/faceted and listwise experiments are separate development adapters. Their results '
        'must not be attributed automatically to the active Supabase index, whose complete-recommendation '
        'chunking and encoder identity still require a controlled deployment reconciliation. The current '
        'clinical source registry remains unapproved; benchmark engineering references are not a '
        'substitute for source review.','',
        'The final evaluation remains on hold. The readiness check requires source-specific '
        'Recall@4 and MRR@4 near 0.80, a balanced development answer pilot covering six families and '
        'three sources, explicit usable-answer coverage, complete audits and fault regressions. '
        'A passage-ranking score does not establish those answer-generation criteria. The earlier '
        'task-aware generation run was stopped after three saved cases, and those cases are not '
        'reported as a completed final study. The clinician bundle provides shuffled evidence panels, '
        'blank relevance and scope forms, a source-linked casebook and a separate engineering triage '
        'queue. Clinical verification and clinical usability remain unperformed.','']
    bge_file=DATA/'bge_reranker/summary.json'
    if bge_file.exists():
        bge_summary=json.loads(bge_file.read_text())
        if not bge_summary.get('complete'):raise ValueError('Incomplete additional reranker results')
        bge=read_csv(DATA/'bge_reranker/intervals.csv')
        lines+=['### 13.4 Additional cross-encoder ablation','',
            'An additional BAAI bge-reranker-v2-m3 cross encoder [17] is tested without changing '
            'the candidate pools, cases or labels. Three declared variants use its direct ordering, '
            'RRF60 with the upstream order plus bounded MMR, and RRF60 with the saved consensus '
            'order plus bounded MMR. Inference uses overlapping windows, frozen weights and CPU '
            'execution. This stage makes no additional Groq calls. The model revision, all ranks, '
            'candidate-recall ceilings, four- and eight-passage results and paired case/family '
            'intervals are retained. It does not constitute final evaluation or answer usability validation.','',
            'Table 23. Additional cross-encoder development results. All declared four-passage '
            'variants are shown; previous consensus values remain in Table 20.','',
            '| Source | Method | Complete / N | Recall@4 | Case 95% CI | Family 95% CI | MRR@4 | Precision@4 |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |']
        for g,total in [('NICE',40),('AAP',30),('WHO',30)]:
            for label,m in [('BGE CE','bge_only'),('BGE upstream RRF/MMR','bge_upstream_rrf_mmr'),('BGE consensus RRF/MMR','bge_consensus_rrf_mmr')]:
                r=row(bge,g,m,4,'recall');mr=row(bge,g,m,4,'mrr');p=row(bge,g,m,4,'precision')
                lines.append(f'| {g} | {label} | {total}/{total} | {n(r["mean"])} | {interval(r,"case")} | {interval(r,"family")} | {n(mr["mean"])} | {n(p["mean"])} |')
        lines+=['','An additional model or rank vote is not assumed to improve retrieval. Negative '
            'changes remain in the paired-difference CSVs. Model-selection comparisons reuse exposed '
            'development cases and cannot establish independent generalization.','']
        lines+=['None of the three additional cross-encoder variants reaches both Recall@4 and '
            'MRR@4 of 0.80 in every guideline source; it is not promoted as the deployment candidate.','']
    fault_file=DATA/'task_aware_faults/interpretation_amendment.json'
    if fault_file.exists():
        f=json.loads(fault_file.read_text())
        if (f['cases'],f['structural_rejections'],f['auditor_calls'])!=(36,36,0):raise ValueError('Update contract-check description')
        lines+=['A separate care-plan contract regression rejects all 36 original free-text fault '
            'challenges at the quote-ID selection schema, before any auditor call. The original '
            'faults are materialized claims rather than valid source selections; this is a structural '
            'contract result and does not measure the revised semantic auditors. The interpretation '
            'amendment, original records and counts are retained.','']
    block='\n'.join(lines)
    if '\n## 13. Subsequent retrieval development' in original:
        before,rest=original.split('\n## 13. Subsequent retrieval development',1)
        _,refs=rest.split('\n## References',1)
        updated=before+'\n'+block+'\n## References'+refs
    else:updated=original.replace('\n## References','\n'+block+'\n## References')
    updated=updated.replace('Updated 27 October 2026','Updated 28 October 2026')
    updated=updated.replace('No retrieval hyperparameter was tuned after results were observed.',
        'No retrieval hyperparameter was tuned within this frozen expanded-100 study; the separately labelled post-hoc development in Section 13 changes the index and retrieval configuration after examining these cases.')
    abstract_note=(' Subsequent development on the same exposed cases obtains consensus Recall@4 of '+', '.join(
        n(row(consensus,g,'consensus',4,'recall')['mean']) for g in ['NICE','AAP','WHO'])+
        ' for NICE, AAP and WHO, respectively; these retrieval-only results do not meet the complete readiness gate, and final evaluation remains on hold.')
    if 'Subsequent development on the same exposed cases obtains consensus Recall@4' not in updated:
        old='evaluator errors limit safety conclusions.'
        updated=updated.replace(old,old+abstract_note,1)
    if '[16] Jin Q' not in updated:
        updated+='\n[16] Jin Q et al. MedCPT: Contrastive Pre-trained Transformers with large-scale PubMed search logs for zero-shot biomedical information retrieval. Bioinformatics 39(11), btad651 (2023). https://doi.org/10.1093/bioinformatics/btad651\n'
    if bge_file.exists() and '[17] BAAI' not in updated:
        updated+='\n[17] BAAI. bge-reranker-v2-m3 model card and inference documentation. https://huggingface.co/BAAI/bge-reranker-v2-m3\n'
    PAPER.write_text(updated,encoding='utf8')
    (ROOT/'docs/research/rag_development_report.md').write_text(block,encoding='utf8')
    published=DATA/'manuscript_before_publication.md'
    baseline=(published if published.exists() else snapshot).read_text(encoding='utf8');changes=[]
    def units(text):
        result=[]
        for line in text.splitlines():
            if not line.strip():continue
            result.extend([line] if line.startswith(('|','#','**','[')) else re.split(r'(?<=[.!?])\s+(?=[A-Z])',line))
        return result
    for line in difflib.ndiff(units(baseline),units(updated)):
        if line.startswith(('- ','+ ')):
            changes.append({'change':'removed' if line[0]=='-' else 'added','sentence_or_table_row':line[2:]})
    with (DATA/'paper_sentence_changes.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=['change','sentence_or_table_row']);w.writeheader();w.writerows(changes)
    print(json.dumps({'updated':'docs/research/manuscript.md','change_rows':len(changes),
        'frozen_tables_preserved':True,'final_evaluation':'on hold'}))


if __name__=='__main__':main()
