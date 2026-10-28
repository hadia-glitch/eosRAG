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
        'not a final evaluation or an untouched test. The original numerical results and tables in Sections 6-7 '
        'remain historical results; methodological scope and annotation-ceiling clarifications do not rerun '
        'that study. No proposed gold identifier or engineering reference answer enters query planning, '
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
    pilot_file=DATA/'patient_conditioned/summary.json'
    dependency_file=DATA/'dependencies/summary.json'
    if pilot_file.exists() and dependency_file.exists():
        pilot_summary=json.loads(pilot_file.read_text())
        dependency_summary=json.loads(dependency_file.read_text())
        if not pilot_summary.get('balanced_pilot_complete') or not dependency_summary.get('balanced_pilot_complete'):
            raise ValueError('No incomplete balanced pilot results in the paper')
        patient=read_csv(DATA/'patient_conditioned/intervals.csv')
        dependency=read_csv(DATA/'dependencies/intervals.csv')
        pilot_snapshot=DATA/'manuscript_before_patient_pilots.md'
        if not pilot_snapshot.exists():pilot_snapshot.write_text(original,encoding='utf8')
        lines+=['### 13.5 Balanced patient-context and dependency pilots','',
            'A subsequent development pilot selects one existing case per source and scenario family, '
            'giving 18 cases and six per source. The original 100 cases and proposed gold identifiers '
            'remain unchanged. This is a complete 18-case pilot, not a completed new 100-case study. '
            'The patient-conditioned ranker receives unchanged recorded current findings and longitudinal '
            'observations alongside the original question; proposed golds and reference answers are '
            'excluded. Its validated identifier selection contributes one fixed RRF60 vote alongside '
            'the upstream candidate order.','',
            'A source-text dependency graph adds candidates linked to explicit diagnostic limitations, '
            'sampling prerequisites or serial-measurement context through shared diagnostic concepts. '
            'These lexical edges retain passage hashes and scope checks, are unreviewed engineering '
            'retrieval hints and do not assert causality or clinical approval. Up to four new candidates '
            'are appended within the same maximum 24-passage budget, trimming the upstream tail if needed. The patient-conditioned prompt is unchanged '
            'in this comparison. Identical unchanged requests reuse their exact saved responses.','',
            'Table 24. Balanced development pilots at four passages. The question-only baseline is '
            'rescored on the same 18 cases, rather than compared to the different 100-case population '
            'in Table 20. Case and whole-family intervals each use 2,000 resamples and seed 31.','',
            '| Source | Method | Complete / N | Recall@4 | Case 95% CI | Family 95% CI | MRR@4 | Precision@4 |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |']
        for g in ['NICE','AAP','WHO']:
            for label,rs,m in [('Question consensus',patient,'question_consensus'),
                               ('Patient consensus',patient,'patient_consensus'),
                               ('Dependency consensus',dependency,'patient_consensus')]:
                r=row(rs,g,m,4,'recall');mr=row(rs,g,m,4,'mrr');p=row(rs,g,m,4,'precision')
                if int(r['completed'])!=6:raise ValueError('Unbalanced pilot source counts')
                lines.append(f'| {g} | {label} | 6/6 | {n(r["mean"])} | {interval(r,"case")} | {interval(r,"family")} | {n(mr["mean"])} | {n(p["mean"])} |')
        lines+=['','No variant in Table 24 meets both 0.80 retrieval entry targets for all sources. '
            'The dependency variant does not increase four-passage recall over patient consensus '
            'and has lower AAP MRR and lower NICE Recall@8; the negative changes remain in the paired '
            'CSV files. It is not promoted on the basis of candidate coverage alone. With only one '
            'case per family per source, these intervals cannot establish broad generalization.','',
            'Table 25. Scoring-only candidate-pool coverage audit on all 100 existing cases, before '
            'and after dependency expansion. A candidate recall ceiling is a limitation of this '
            'retrieval stage, not a natural metric ceiling or a basis for normalizing reported recall.','',
            '| Source | Complete / N | Cases missing gold: before | After | Candidate recall ceiling: before | After |',
            '| --- | --- | --- | --- | --- | --- |']
        before_coverage=read_csv(DATA/'patient_conditioned/candidate_coverage_by_source.csv')
        after_coverage=read_csv(DATA/'dependencies/candidate_coverage_by_source.csv')
        for g in ['NICE','AAP','WHO']:
            b=next(r for r in before_coverage if r['guideline']==g)
            a=next(r for r in after_coverage if r['guideline']==g)
            lines.append(f'| {g} | {b["completed"]}/{b["total"]} | {b["cases_with_missing_gold"]} | {a["cases_with_missing_gold"]} | {n(b["mean_candidate_recall_ceiling_at_4"])} | {n(a["mean_candidate_recall_ceiling_at_4"])} |')
        lines+=['','Missing annotated passages cannot be recovered by a downstream ranker when they '
            'are absent from its candidate pool. Recovering them does not guarantee correct ordering '
            'or clinical usefulness. Proposed gold sets may omit other useful passages or include '
            'conditional recommendations whose patient prerequisites are unknown; independent '
            'adjudication remains necessary. Transport blocks are pending operational events rather '
            'than scored clinical failures. Final evaluation and integration of a newly evaluated application pipeline '
            'remain pending the declared readiness criteria.','']
        stopped=DATA/'evidence_sets/stop_amendment.json'
        if stopped.exists():
            stopped_summary=json.loads(stopped.read_text())
            quote_records=[json.loads(p.read_text()) for p in (DATA/'evidence_sets/runs').glob('*.json')]
            id_records=[json.loads(p.read_text()) for p in (DATA/'evidence_ids/runs').glob('*.json')]
            rejected=sum(not r['available'] for r in quote_records)
            valid=sum(r['available'] for r in id_records)
            lines+=['A further evidence-set pilot requests a relevance purpose, essential/supporting '
                'distinction and exact source quotation for every choice. It is stopped after '
                f'{len(quote_records)} completed responses, with {rejected} contract rejections; '
                'abbreviated or altered quotations are not repaired into successful model outputs. '
                'A separate version returns immutable passage identifiers and materializes full source '
                f'text in application code. That old-corpus pilot has {len(id_records)} completed NICE cases '
                f'and {valid} structurally valid selections. It is not a balanced completed experiment '
                'or clinical quality evaluation. Remaining calls are deferred while source-boundary '
                'corrections and local retrieval checks are completed, conserving cloud tokens.','']
    corrected_file=DATA/'recommendation_units/faceted/summary.json'
    guarded_file=DATA/'recommendation_units/guarded_facets/summary.json'
    if corrected_file.exists() and guarded_file.exists():
        if not all(json.loads(p.read_text()).get('complete') for p in [corrected_file,guarded_file]):
            raise ValueError('No incomplete corrected-corpus study in the manuscript')
        corrected=read_csv(corrected_file.parent/'intervals.csv')
        guarded=read_csv(guarded_file.parent/'intervals.csv')
        boundary=read_csv(corrected_file.parent/'source_boundary_paired_differences.csv')
        anchor=read_csv(guarded_file.parent/'anchor_guard_paired_differences.csv')
        counts=read_csv(corrected_file.parent/'source_boundary_counts.csv')
        changed=sum(int(r['changed_source_texts']) for r in counts)
        lines+=['### 13.6 Source-boundary correction and bounded facet anchors','',
            f'A source-traceable structural amendment changes {changed} NICE passages without changing '
            'the 299 passage identifiers, original 100 cases or gold identifiers. Numbered recommendations '
            'are separated from following risk-factor or clinical-indicator boxes, Box 1 starts at its '
            'own title, and Box 2 includes its continuation on the next supplied-PDF page. Trailing '
            'numbered section headings are removed. Each repaired unit retains supplied-PDF pages, '
            'offsets in a declared footer-stripped extraction stream and hashes of the text and PDF. '
            'Four unnumbered trailing major headings remain flagged as extraction context; this is '
            'not a claim of a perfect PDF parser or clinical source approval.','',
            'NICE retrieval is recomputed with the preceding model/query settings. AAP and WHO source '
            'payloads are exactly unchanged and retain their preceding saved rankings in this '
            'source-boundary comparison, explicitly labelled as replays rather than independent '
            'replication. The amendment uses no new Groq calls. It is retained for source completeness '
            'even when annotation-overlap scores decrease.','',
            'Table 26. NICE source-boundary amendment, all 40 cases. Prior values are quoted from the '
            'preceding faceted development CSVs; the paired interval describes corrected minus prior '
            'Recall@4. All five declared variants and both interval types are retained.','',
            '| Method | Complete / N | Prior Recall@4 | Corrected Recall@4 | Change | Case 95% CI | Family 95% CI | Corrected MRR@4 |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |']
        methods=[('Generic single','generic_single'),('Medical single','medical_single'),
                 ('Generic faceted','generic_faceted'),('Medical faceted','medical_faceted'),
                 ('Medical faceted graph','medical_faceted_graph')]
        for label,m in methods:
            old=row(facet,'NICE',m,4,'recall');new=row(corrected,'NICE',m,4,'recall')
            difference=next(r for r in boundary if (r['guideline'],r['method'],r['depth'],r['metric'])==('NICE',m,'4','recall'))
            mr=row(corrected,'NICE',m,4,'mrr')
            lines.append(f'| {label} | 40/40 | {n(old["mean"])} | {n(new["mean"])} | {n(difference["mean"])} | {interval(difference,"case")} | {interval(difference,"family")} | {n(mr["mean"])} |')
        lines+=['','The preceding facet selector can force an anchor outside the original-question '
            'relevance head. A separate bounded variant admits a facet anchor only if it belongs '
            'to both the fused and original-question top twice-the-return-budget heads. RRF offset '
            '60, model weights, queries, cases, golds and MMR diversity remain unchanged. All 100 '
            'orders are recomputed using exact cached cross-encoder scores; query embeddings are '
            'recomputed locally, with no new cross-encoder or Groq calls.','',
            'Table 27. Bounded-anchor development on the corrected corpus. Paired change is bounded '
            'minus unguarded Recall@4. Negative changes remain visible, and these estimates reuse '
            'the exposed development cases.','',
            '| Source | Method | Complete / N | Prior Recall@4 | Bounded Recall@4 | Change | Case 95% CI | Family 95% CI | Bounded MRR@4 |',
            '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
        for g,total in [('NICE',40),('AAP',30),('WHO',30)]:
            for label,m in methods[2:]:
                old=row(corrected,g,m,4,'recall');new=row(guarded,g,m,4,'recall');mr=row(guarded,g,m,4,'mrr')
                difference=next(r for r in anchor if (r['guideline'],r['method'],r['depth'],r['metric'])==(g,m,'4','recall'))
                lines.append(f'| {g} | {label} | {total}/{total} | {n(old["mean"])} | {n(new["mean"])} | {n(difference["mean"])} | {interval(difference,"case")} | {interval(difference,"family")} | {n(mr["mean"])} |')
        if any(all(float(row(guarded,g,m,4,metric)['mean'])>=.8 for g in ['NICE','AAP','WHO'] for metric in ['recall','mrr']) for _,m in methods):
            raise ValueError('Update readiness interpretation for a passing retrieval variant')
        lines+=['','The bounded medical-faceted variant has higher NICE Recall@4 than its unguarded '
            'corrected-corpus counterpart, but lower AAP Recall@4; WHO is unchanged. No declared '
            'variant meets both retrieval targets for every guideline. These structural repairs '
            'and mixed retrieval changes do not establish usable care-plan coverage, semantic fault '
            'robustness or clinical validation. Local-model development and transport compatibility '
            'are separate from a completed final generation evaluation. The final evaluation remains '
            'on hold, followed by integration of the evaluated pipeline and publication.','']
    topic_file=DATA/'recommendation_units/topic_scope/summary.json'
    smoke_file=DATA/'recommendation_units/scoped_primary_smoke/summary.json'
    if topic_file.exists():
        topic_summary=json.loads(topic_file.read_text())
        if not topic_summary.get('complete'):raise ValueError('Incomplete source-topic comparison')
        topic=read_csv(topic_file.parent/'intervals.csv')
        changes=read_csv(topic_file.parent/'paired_differences.csv')
        lines+=['### 13.7 Source-topic routing and capped primary-model smoke','',
            'A separate source-topic routing ablation removes unrequested future-pregnancy counselling, '
            'maternal labour-management topics and CSF-result interpretation without requested or '
            'recorded CSF context from the current-case lane. It preserves explicit searches for those '
            'topics. These engineering topic labels remain subject to clinical review; they do not '
            'infer patient eligibility or grant source approval. All 100 cases and golds are retained, '
            'with zero topic/gold exclusion conflicts. Vacated slots are refilled from the same '
            'method\'s saved depth-12 order. No new model calls are used.','',
            'Table 28. Medical-faceted topic-routing results. Both preceding selector variants are '
            'retained. The paired change is topic routing minus its corresponding parent Recall@4; '
            'all methods, eight-passage results and uncertainty estimates remain in CSVs.','',
            '| Source | Parent | Complete / N | Recall@4 | Change | Case 95% CI | Family 95% CI | MRR@4 |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |']
        for g,total in [('NICE',40),('AAP',30),('WHO',30)]:
            for parent in ['faceted','guarded_facets']:
                def topic_row(rs,metric):return next(r for r in rs if (r['guideline'],r['parent'],r['method'],r['depth'],r['metric'])==(g,parent,'medical_faceted','4',metric))
                recall=topic_row(topic,'recall');mr=topic_row(topic,'mrr');difference=topic_row(changes,'recall')
                lines.append(f'| {g} | {parent.replace("_"," ")} | {total}/{total} | {n(recall["mean"])} | {n(difference["mean"])} | {interval(difference,"case")} | {interval(difference,"family")} | {n(mr["mean"])} |')
        lines+=['','Source-topic routing has higher NICE overlap estimates in this benchmark, but '
            'does not meet the complete per-source retrieval gate. It is not evidence that every '
            'topic exclusion is clinically correct; the excluded source passages are exported for '
            'review.','']
    if smoke_file.exists():
        smoke=json.loads(smoke_file.read_text())
        smoke_rows=read_csv(smoke_file.parent/'per_case.csv')
        lines+=['A capped primary-model smoke check makes at most three unique retrieval-ranking '
            'requests, one deliberately selected difficult case per source. It uses the corrected '
            'corpus and source-topic routing with GPT-OSS-120B, temperature zero, completion budget '
            '2,000 and RRF offset 60. No generator, claim-auditor or answer-judge calls are made. '
            f'All {smoke["completed"]}/{smoke["total"]} requests complete, with {smoke["selector_valid"]} '
            'structurally valid selections; validity includes an empty selection and is not answer '
            'usability. No population interval is inferred from one selected case per source.','',
            'Table 29. Descriptive capped smoke results, preserving unsuccessful reranking. '
            'Candidate order is the baseline from the same source packet, not a different cohort.','',
            '| Case | Complete / N | Candidate Recall@4 | Selected Recall@4 | Consensus Recall@4 | Selected MRR@4 |',
            '| --- | --- | --- | --- | --- | --- |']
        for case_id in ['single_risk-1','aap-expanded-missing_results-01','who-expanded-incomplete_stop-01']:
            rs={r['method']:r for r in smoke_rows if r['id']==case_id and r['depth']=='4'}
            lines.append(f'| {case_id} | 1/1 | {n(rs["candidate_order"]["recall"])} | {n(rs["selected"]["recall"])} | {n(rs["consensus"]["recall"])} | {n(rs["selected"]["mrr"])} |')
        lines+=['','The language-model ranking stage is not promoted: a valid identifier contract '
            'does not prevent omission of annotated evidence or an empty selection on a source-limitation '
            'question. Completed model outcomes remain in quality results; local inference timeouts '
            'and provider rate limits remain pending operational events. Final evaluation remains '
            'on hold rather than interpreting three valid contracts as clinical readiness.','']
    structured_file=DATA/'structured_context/summary.json'
    if structured_file.exists():
        structured=json.loads(structured_file.read_text())
        if not structured.get('complete'):raise ValueError('Incomplete source-context study')
        sr=read_csv(structured_file.parent/'intervals.csv')
        sp=read_csv(structured_file.parent/'paired_differences.csv')
        sem=read_csv(DATA/'semantic_guidance/intervals.csv')
        lines+=['### 13.8 Publisher hierarchy, qualification links and recorded history','',
            'A subsequent offline comparison scores all source-, population- and topic-admitted guidance '
            'candidates with the existing medical and generic cross encoders. RRF offset 60 combines their '
            'rankings; weak lexical and dense votes no longer displace high cross-encoder candidates in this '
            'ablation. Source-extracted definitions enrich scoring text while original recommendation wording '
            'remains immutable. The full-pool, genre-plus-facet and definition variants are retained, including '
            'negative results. Genre and facet anchoring change together and cannot be interpreted as an isolated '
            'genre effect. WHO definition-graph Recall@4 is '+n(row(sem,'WHO','ce_definition_graph',4,'recall')['mean'])+
            ', compared with '+n(row(sem,'WHO','ce_guidance_genre',4,'recall')['mean'])+
            ' for genre-plus-facet selection; AAP remains below the retrieval target in that comparison.','',
            'The next selector prioritizes explicit publisher conclusion paragraphs by the information needs '
            'expressed in the question. A source-context graph connects a serial-marker recommendation to its '
            'interpretation limitation, a shared treatment-start sampling condition, or reassessment guidance '
            'under the same publisher heading. These are engineering context links, not causal relationships '
            'or clinician-approved treatment rules. A separate history ablation adds context only when actual '
            'prior marker observations are available and the question requests uncertainty or serial interpretation. '
            'Missing, duplicate and future observation times cannot establish a serial history. Every selected '
            'recommendation consumes a top-k slot; supplemental definition nodes and their word counts are '
            'reported separately in CSVs. A single stable ordering is used at four and eight passages.','',
            'Table 30. Source-context development ablation on unchanged cases and golds. All retrieval runs '
            'complete; answer release coverage is not measured by this table.','',
            '| Source | Complete / N | Hierarchy R@4 | Qualification R@4 | History R@4 | History MRR@4 | History nDCG@4 |',
            '| --- | --- | --- | --- | --- | --- | --- |']
        for g,total in [('NICE',40),('AAP',30),('WHO',30)]:
            vals=[row(sr,g,m,4,'recall')['mean'] for m in ['publisher_hierarchy','qualifier_graph','longitudinal_context_graph']]
            vals+=[row(sr,g,'longitudinal_context_graph',4,m)['mean'] for m in ['mrr','ndcg']]
            lines.append('| '+g+f' | {total}/{total} | '+' | '.join(n(v) for v in vals)+' |')
        lines+=['','Table 31. Conventional eight-passage metrics for the longitudinal source-context variant.','',
            '| Source | Complete / N | Recall@8 | Precision@8 | MRR@8 | nDCG@8 |',
            '| --- | --- | --- | --- | --- | --- |']
        for g,total in [('NICE',40),('AAP',30),('WHO',30)]:
            vals=[row(sr,g,'longitudinal_context_graph',8,m)['mean'] for m in ['recall','precision','mrr','ndcg']]
            lines.append('| '+g+f' | {total}/{total} | '+' | '.join(n(v) for v in vals)+' |')
        lines+=['','Table 32. Recall uncertainty and explicitly quoted preceding paper values. Changes '
            'compare the new longitudinal variant with the preceding corrected-corpus medical-faceted topic '
            'selector, not a controlled same-index component effect. All intervals use 2,000 resamples, seed 31.','',
            '| Source | Old R@4 | New R@4 | Paired change | Case 95% CI | Family 95% CI |',
            '| --- | --- | --- | --- | --- | --- |']
        for g in ['NICE','AAP','WHO']:
            old=next(r for r in topic if (r['guideline'],r['parent'],r['method'],r['depth'],r['metric'])==(g,'guarded_facets','medical_faceted','4','recall'))
            diff=next(r for r in sp if (r['guideline'],r['method'],r['depth'],r['metric'],r['contrast'])==
                (g,'longitudinal_context_graph','4','recall','new method minus prior medical-faceted topic scope'))
            new=row(sr,g,'longitudinal_context_graph',4,'recall')
            lines.append(f'| {g} | {n(old["mean"])} | {n(new["mean"])} | {n(diff["mean"])} | {interval(diff,"case")} | {interval(diff,"family")} |')
        history_delta=next(r for r in sp if (r['guideline'],r['method'],r['depth'],r['metric'],r['contrast'])==
            ('NICE','longitudinal_context_graph','4','recall','longitudinal_context_graph minus qualifier_graph'))
        lines+=['','The NICE history-minus-qualification Recall@4 difference is '+n(history_delta['mean'])+
            ' (case 95% interval '+interval(history_delta,'case')+'; family 95% interval '+interval(history_delta,'family')+
            '). The history contribution is not a demonstrated general improvement when its interval includes '
            'zero. The hierarchy accounts for the AAP overlap increase; it must not be attributed to history '
            'or graph traversal. All source-specific MRR, nDCG and precision intervals and remaining misses '
            'are preserved in the per-case and paired-result CSVs.','',
            'The annotation-defined mean Precision@8 ceiling is 0.3344 for NICE and 0.2500 for AAP and WHO, '
            'because the gold sets contain few relevant identifiers. Precision is not rescaled to one. '
            'Unlabelled passages may still be clinically relevant and require adjudication. Recall, MRR '
            'and nDCG can reach one in these cases; they have no corresponding low annotation ceiling. '
            'Perfect AAP/WHO recall and degenerate bootstrap bounds reflect these repeated templates, broad '
            'publisher-summary golds and small source pools, not perfect clinical retrieval.','',
            'This candidate clears the prespecified mean retrieval entry targets on the exposed development '
            'cases, but the complete readiness gate remains unmet. Balanced answer usability, complete semantic '
            'audits, fresh semantic fault injection, source/gold adjudication and external validation remain '
            'pending. No new Groq calls are used in the source-context comparison. Subsequent source-hash, '
            'heading, role and cross-document-edge hardening reproduces all 100 cases across three methods '
            'and both depths without changed rankings. The candidate is not a final evaluated or deployed '
            'pipeline.','']
    pic=ROOT/'output/research/pic_longitudinal/model_comparison.json'
    if pic.exists():
        pr=json.loads(pic.read_text());audit=json.loads((pic.parent/'cohort_audit.json').read_text())
        lines+=['### 13.9 Actual-data longitudinal model development and maternal-data gap','',
            f'A separate local PIC v1.1.0 analysis [18] yields {pr["patients"]} infants, '
            f'{pr["positive_patients"]} independent positive infants and {pr["landmarks"]} eligible prediction '
            'landmarks. The research endpoint is a documented named bacterial pathogen in blood collected '
            'before 72 hours, not adjudicated clinical EOS. Explicit bacterial no-growth reports define '
            'controls; missing, fungal-only, preliminary and possible-contaminant reports are not labelled '
            'as negative. Predictions precede the first early blood culture. Measurement availability uses '
            'the later of chart and storage time; both must precede the landmark. Untimed discharge diagnoses, '
            'organisms, medication orders and later outcomes are excluded as predictors. Laboratory values '
            'are excluded because result availability cannot be established from collection time alone.','',
            'Snapshot logistic regression is compared with actual elapsed-time trends, six four-hour '
            'history bins, a shallow trend forest and an equal-weight longitudinal ensemble. Training-only '
            'median imputation, scaling, missingness indicators and variable-feature selection are repeated '
            'within three patient-stratified folds. Each infant has equal total landmark weight. Candidate '
            'selection uses cross-validated AUPRC and has no independent test. A recurrent network is not '
            'fitted below the declared engineering event floor. More landmarks from the same infant do not '
            'supply additional independent positive outcomes.','',
            'Table 33. PIC development comparison. The patient count is '+str(pr['patients'])+
            ' and the positive-infant count is '+str(pr['positive_patients'])+
            ' for every row. Patient-bootstrap intervals use 2,000 resamples; single-class draws are omitted '
            'and their counts are recorded.','',
            '| Method | AUROC | AUROC 95% CI | AUPRC | Brier |',
            '| --- | --- | --- | --- | --- |']
        for method,v in pr['comparison'].items():
            m=v['metrics'];ci=v['bootstrap']['intervals']['auroc']
            lines.append(f'| {method.replace("_"," ")} | {n(m["auroc"])} | [{n(ci[0])}, {n(ci[1])}] | {n(m["auprc"])} | {n(m["brier"])} |')
        lines+=['','The new real-data model is withheld from clinical risk decisions because discrimination '
            'is inadequate and the event count is small. The missingness-only comparator is competitive, '
            'raising concern about recording-process signals. No probability is labelled a calibrated EOS '
            'risk, and no treatment threshold is endorsed. The raw model and individual predictions remain '
            'local under the credentialed data agreement; public outputs contain aggregate statistics only.','',
            'PIC does not provide the required linked maternal predictor set in the selected structured '
            'tables. The earlier maternal/perinatal and clinical synthetic experiment remains separate '
            'from PIC. No synthetic maternal record is attached to a real infant and no blended real/synthetic '
            'EOS probability is produced. The synthetic combined score can reproduce label-conditional '
            'symptom generation and does not resolve the real-data performance gap. GBS, intrapartum '
            'temperature, rupture duration and antibiotic timing require linked obstetric-neonatal observations '
            'before their joint predictive effects can be estimated. A research input contract retains '
            'unknown values, explicit measurement/availability times and an auditable field-use distinction; '
            'input completeness is not model validation. Clinical verification has not been performed.','']
    robustness=DATA/'canonical_router_repair/fresh/summary.json'
    if robustness.exists():
        from robustness_paper_sections import sections
        lines += [sections()]
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
    latest=abstract_note.strip()
    if structured_file.exists():
        latest=('Subsequent development on the same exposed cases obtains longitudinal source-context Recall@4 of '+
            ', '.join(n(row(sr,g,'longitudinal_context_graph',4,'recall')['mean']) for g in ['NICE','AAP','WHO'])+
            ' for NICE, AAP and WHO, respectively; these retrieval results clear the mean retrieval entry targets, '
            'while answer usability and semantic safety remain unestablished and final evaluation remains on hold.')
    abstract_before,after_keywords=updated.split('\n\n**Keywords:**',1)
    abstract_before=re.sub(r'\s*Subsequent development on the same exposed cases obtains (?:consensus|longitudinal source-context) Recall@4[^\n]*?final evaluation remains on hold\.','',abstract_before)
    abstract_before=re.sub(r'\s*A separate actual-data PIC longitudinal development cohort contains[^\n]*?clinical risk decisions\.','',abstract_before)
    abstract_before=re.sub(r'\s*A subsequent wording audit on those same cases finds[^\n]*?clinical readiness remains? unestablished\.','',abstract_before)
    abstract_before=abstract_before.rstrip()+' '+latest
    if pic.exists():
        note=(f' A separate actual-data PIC longitudinal development cohort contains {pr["patients"]} infants '
            f'and {pr["positive_patients"]} independent positive infants; its best AUROC among the prespecified '
            'predictive candidates is '+n(max(pr['comparison'][m]['metrics']['auroc'] for m in ['snapshot_logistic','trend_logistic','binned_logistic','trend_forest']))+
            ', so the new model is withheld from clinical risk decisions.')
        abstract_before+=note
    if robustness.exists():
        abstract_before+=(' A subsequent wording audit on those same cases finds NICE Recall@4 falls '
            'from 0.9167 to 0.7667 with plain-language queries; a three-case explanation smoke test '
            'also identifies a source-exception omission despite model-auditor agreement, so '
            'generalisation and clinical readiness remain unestablished.')
    updated=abstract_before+'\n\n**Keywords:**'+after_keywords
    if '[16] Jin Q' not in updated:
        updated+='\n[16] Jin Q et al. MedCPT: Contrastive Pre-trained Transformers with large-scale PubMed search logs for zero-shot biomedical information retrieval. Bioinformatics 39(11), btad651 (2023). https://doi.org/10.1093/bioinformatics/btad651\n'
    if bge_file.exists() and '[17] BAAI' not in updated:
        updated+='\n[17] BAAI. bge-reranker-v2-m3 model card and inference documentation. https://huggingface.co/BAAI/bge-reranker-v2-m3\n'
    if pic.exists() and '[18] Li H' not in updated:
        updated+='\n[18] Li H, Zeng X, Yu G. Paediatric Intensive Care database (version 1.1.0). PhysioNet (2020). https://doi.org/10.13026/32x9-wv38\n'
    if robustness.exists() and '[19] Nguyen' not in updated:
        updated+='\n[19] Nguyen et al. Effective diagnosis of sepsis in critically ill children using probabilistic graphical model. Translational Pediatrics 12(4):538–551 (2023). https://doi.org/10.21037/tp-22-510\n'
    if robustness.exists() and '[20] Friedman' not in updated:
        updated+='\n[20] Friedman N, Geiger D, Goldszmidt M. Bayesian Network Classifiers. Machine Learning 29:131–163 (1997). https://ai.stanford.edu/~nir/Abstracts/FrGG1.html\n'
    if (ROOT/'output/research/new_neonatal_cohorts/results.json').exists():
        if '[21] GM S' not in updated:
            updated+='\n[21] GM S, Renganathan G, D\'sa S. Accuracy of Systemic Inflammatory Indices in identifying Neonatal Sepsis in preterms in a tertiary care hospital in Mangalore. F1000Research 14:390, version 4. https://f1000research.com/articles/14-390/v4 ; underlying dataset https://doi.org/10.6084/m9.figshare.28395161.v1\n'
        if '[22] Ostapenko' not in updated:
            updated+='\n[22] Ostapenko S et al. Neonatal sepsis registry: Time to antibiotic dataset. Data in Brief 27:104788 (2019). https://doi.org/10.1016/j.dib.2019.104788\n'
    if (ROOT/'output/research/bmj_boruta_adaptation/results.json').exists() and '[23] Kainth' not in updated:
        updated+='\n[23] Kainth D et al. A machine learning model for prediction of early-onset neonatal sepsis in low-income and middle-income countries: development and validation study. BMJ Paediatrics Open 10:e003561 (2026). https://doi.org/10.1136/bmjpo-2025-003561\n'
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
