"""Build a measured Phase 1 addendum; incomplete quality populations stop export."""
import argparse,csv,json,math
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/research/phase1_pilot'

def read(path):return json.loads(path.read_text(encoding='utf8'))
def rows(name):return list(csv.DictReader((OUT/name).open(encoding='utf-8-sig')))
def table(headers,body):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(map(str,r))+' |' for r in body])
def num(v,d=3):return 'NOT EVALUATED' if v=='NOT EVALUATED' else f'{float(v):.{d}f}'
def avg(rs,k,arm):
    values=[r[k] for r in rs if r['arm']==arm]
    return 'NOT EVALUATED' if not values or 'NOT EVALUATED' in values else mean(float(v) for v in values)
def rate(rs,k,arm):
    values=[r[k] for r in rs if r['arm']==arm]
    return 'NOT EVALUATED' if not values or 'NOT EVALUATED' in values else mean(str(v).lower()=='true' for v in values)
def flags(rs,k,arm):
    values=[r[k] for r in rs if r['arm']==arm]
    return 'NOT EVALUATED' if not values or 'NOT EVALUATED' in values else mean(bool(json.loads(v)) for v in values)

def main(allow_partial=False):
    progress=read(OUT/'progress.json')
    if not progress['complete'] and not allow_partial:raise RuntimeError('Pilot quality populations incomplete; final paper not exported.')
    complete=progress['complete']
    manifest=read(OUT/'manifest.json');audit=read(ROOT/'output/research/probability_audit/audit.json')
    original=read(ROOT/'output/research/data_audit.json');leak=read(ROOT/'output/research/leakage_audit/audit.json')['experiments']['postnatal_days_0_2']
    evaluation=read(ROOT/'output/research/postnatal_days_0_2/evaluation.json')
    metric=read(OUT/'generation_metrics.json');inputs=read(OUT/'inputs.json')
    analysis=read(OUT/'analysis.json') if (OUT/'analysis.json').exists() else None
    exact=rows('01_pilot_exact_retrieval.csv');semantic=rows('03_pilot_semantic_summary.csv')
    usability=rows('04_pilot_clinical_usability.csv');generation=rows('05_pilot_generation.csv');ma=rows('06_pilot_multiagent.csv')
    arms=['dense','sparse','vector','graph','hybrid'];lines=[];add=lines.append
    add('# NeoGuard: Phase 1 Pilot Evaluation and Model Probability Audit'+('' if complete else ' (Interim)'))
    add('**Technical research addendum | 25-26 October 2026 | Ten fixed synthetic cases; actual saved rankings and plans; fresh judgments and metrics.**')
    add('## 1. Decision and scope')
    if not complete:add(f'**INCOMPLETE PLAN ASSESSMENT.** Retrieval and text metrics are complete. Source-separated plan judging has saved {progress["fresh_plan_stage_judgments"]}/80 stages and completed {progress["fresh_plan_judgments"]}/40 full plan assessments. Pending analyses are NOT EVALUATED, never zero-filled. This interim artifact is not the completed pilot decision.')
    add(('**REVISE.**' if complete else '**Provisional readiness assessment: REVISE.**')+' The saved graph/hybrid rankings show promising retrieval on this small development pilot. They do not establish clinical safety, a controlled multi-agent benefit, or a valid EOS prediction probability. Correct the benchmark/source/citation provenance and establish a defensible clinical model cohort before expansion or clinical release.')
    add(f'The ten cases contain four NICE, three WHO and three AAP scenarios. They include low and critical recorded risk categories, renal-safety, penicillin-allergy, low-birth-weight and recent-hospitalization scenarios, and longitudinal change. Selection was deterministic, metadata-based, and frozen before judging. All {progress["fresh_unique_chunk_judgments"]} unique case/passage judgments were completed and mapped back to the actual top-ten lists.')
    add('## 2. Methods and traceability')
    add('The canonical 100-case JSON, three historical result CSVs and the benchmark-declared chunks_ingested.csv were hashed. The gold evidence was preserved. Twelve selected historical rows disagree with canonical gold; the manifest lists every mismatch. All selected top-ten and gold chunk IDs resolve in the 489-row corpus. The five named arms are interpreted as saved labels; their Dense/Vector implementation distinction and full controlled-ablation provenance are not established by the CSVs.')
    collision=read(OUT/'source_id_collision_audit.json')
    add(f'The {collision["source_rows"]} source rows contain {collision["distinct_ids"]} distinct identifiers and {collision["duplicate_id_groups"]} conflicting-text ID groups. Three colliding IDs affect AAP cases 003, 007 and 011. The frozen input mapping used the last CSV occurrence, which the audit independently verified; all variants are preserved. Exact-ID scores cannot disambiguate conflicting content, and semantic/source scores are conditional on the frozen texts. No input or gold was changed after this discovery. Resolve these identities before a confirmatory experiment.')
    add('All ten original selected cases omit postnatal age. That prevents confirmation of EOS age eligibility and some age-specific treatment conditions. Missing age was kept unknown in the evaluator inputs; no corrected case facts were substituted. A high automated clinical rating despite this missing scope information is a limitation of the evaluator, not evidence that eligibility was established.')
    add('Exact MRR@10 uses the first canonical gold hit. NDCG@10 uses binary gain and a standard gold-normalized ideal ranking from all canonical gold IDs, capped at ten; missing ranks have zero relevance and duplicates do not receive repeated credit. Expanded context is excluded. Fifty NDCG values independently matched scikit-learn within 1e-12. Anchor recall is normalized exact phrase coverage, not a measure of clinical correctness.')
    add('GPT-OSS-120B at temperature zero judged actual chunk text, case, active guideline and gold evidence with arm labels hidden. Grade >=2 defines useful evidence. Semantic NDCG uses graded gains and the same judged union of the five top-ten lists as each case\'s ideal pool; it is not a corpus-wide ideal. Scores and rationales are retained per chunk. This is an LLM-based clinical usability assessment - not clinician validation.')
    add(('All four saved plan arms were freshly assessed' if complete else 'The final plan assessment is specified')+' under a source-separated rubric-4 protocol. The grounding pass receives ONLY actual retrieved plan evidence. A separate clinical-usefulness pass receives the case and wider guideline evidence. Unsupported claims and contradictions select immutable candidate-line IDs, materialized locally as exact quotations; omissions are separate. Exploratory earlier judgments, including a gold-versus-retrieved-context confusion, remain archived and are excluded. Historical MA traces lack a verified E-number-to-passage mapping; the evaluator must not invent one. Saved Dense/Hybrid/MA generations differ, so this is a composite historical comparison, not an identical-draft verification ablation or an estimate of an individual agent\'s effect.')
    add('## 3. Retrieval results')
    add(table(['Arm','Exact MRR@10','Exact NDCG@10','Anchor recall','Useful P@10','Semantic NDCG@10'],[
        [a.title(),num(avg(exact,'exact_mrr_at10',a)),num(avg(exact,'exact_ndcg_at10',a)),num(avg(exact,'anchor_grounding_recall',a)),
         num(next(r for r in semantic if r['arm']==a)['utility_precision_at10']),num(next(r for r in semantic if r['arm']==a)['semantic_ndcg_at10'])] for a in arms]))
    add('Graph ranks the first exact gold hit most effectively; Hybrid ranks the total exact and graded evidence pool slightly better. Graph and Hybrid tie on useful precision. The small sample and dependent source/reference construction preclude a general superiority claim. Semantic and exact results favor graph/hybrid overall but do not give identical arm orderings.')
    if analysis:
        comparison=analysis['paired_comparisons']['retrieval_exact_ndcg_at10']
        lo,hi=comparison['bootstrap_percentile_95']
        add(f'Hybrid minus Dense exact NDCG is {comparison["mean_difference"]:.3f}; a descriptive paired case bootstrap (20,000 resamples, seed 20261025) gives a 95% percentile interval [{lo:.3f}, {hi:.3f}]. This interval does not resolve template/source dependence or imply clinical generalizability. Exact and semantic arm-mean NDCG ranks have Spearman correlation {analysis["exact_versus_semantic_ndcg_arm_rank_spearman"]:.2f}.')
    add(table(['Case','Guideline','Dense exact NDCG','Hybrid exact NDCG','Dense useful P@10','Hybrid useful P@10'],[
        [c['case_id'],c['active_guideline'],*[
            num(next(r for r in exact if r['case_id']==c['case_id'] and r['arm']==a)['exact_ndcg_at10']) for a in ['dense','hybrid']],
         *[num(next(r for r in progress['semantic_per_case'] if r['case_id']==c['case_id'] and r['arm']==a)['utility_precision_at10']) for a in ['dense','hybrid']]] for c in inputs['cases']]))
    add(f'The fresh evaluator produced {len(progress["judge_relevance_applicability_disagreements"])} recorded relevance/applicability/usefulness inconsistencies. Protocol usefulness is computed from grade >=2; raw conflicting booleans and rationales remain available. Relevant treatment text can still be inapplicable to a particular infant, and model judgments must not override population or safety gates.')
    add('## 4. Generated-plan usability and similarity')
    scorekeys=['faithfulness','citation_correctness','citation_completeness','clinical_correctness','clinical_completeness','clinical_utility','safety']
    if complete:
        add(table(['Fresh 1-5 assessment','Dense','Hybrid'],[[k.replace('_',' ').title(),num(avg(usability,k,'dense')),num(avg(usability,k,'hybrid'))] for k in scorekeys]))
        add(table(['Case','Guideline','Dense utility','Hybrid utility','Dense safety','Hybrid safety'],[
            [c['case_id'],c['active_guideline'],*[num(next(r for r in usability if r['case_id']==c['case_id'] and r['arm']==a)[k],1) for k in ['clinical_utility','safety'] for a in ['dense','hybrid']]] for c in inputs['cases']]))
    else:add('Final full-plan usability ratings are NOT EVALUATED yet. Earlier exploratory scores exposed evaluator scope/quotation defects and are not substituted for the pending source-separated ratings. The numerical results below are completed text-similarity measurements only.')
    add(table(['Fresh metric','Dense','Hybrid'],[[k,num(avg(generation,k,'dense')),num(avg(generation,k,'hybrid'))] for k in ['bleu','meteor','bertscore_f1','anchor_grounding_recall']]))
    add(f'Fresh ROUGE-L F1 is {mean(r["rouge_l"] for r in metric["records"] if r["arm"]=="dense_only"):.4f} for Dense and {mean(r["rouge_l"] for r in metric["records"] if r["arm"]=="hybrid"):.4f} for Hybrid.')
    add(f'BLEU is sentence BLEU-4 divided by 100 with the 13a tokenizer and exponential smoothing. METEOR uses lowercased WordPunct tokens and default Porter/WordNet matching. DistilBERT BERTScore uses layer 5, no IDF and no baseline rescaling. Standard backbone truncation affects {metric["truncated_pairs"]}/20 pairs. Full plan text is retained for usability review. The reference is a deterministic template, not independent clinical ground truth; Dense\'s slightly higher similarity scores do not establish better care.')
    add('## 5. Multi-agent results and safety interpretation')
    ma_rows=[
        ['Reported trace verification rate',num(rate(ma,'factcheck_verified','dense_ma')),num(rate(ma,'factcheck_verified','hybrid_ma'))],
        ['Reported trace mean confidence',num(avg(ma,'confidence','dense_ma')),num(avg(ma,'confidence','hybrid_ma'))],
        ['Reported mean resolution steps',num(avg(ma,'resolution_steps','dense_ma')),num(avg(ma,'resolution_steps','hybrid_ma'))],
        ['Fresh regimen-incomplete rate',num(rate(ma,'regimen_incomplete','dense_ma')),num(rate(ma,'regimen_incomplete','hybrid_ma'))],
        ['Fresh ungrounded-dose rate',num(rate(ma,'ungrounded_dose','dense_ma')),num(rate(ma,'ungrounded_dose','hybrid_ma'))],
        ['Fresh unsupported-claim plan rate',num(flags(ma,'unsupported_claims','dense_ma')),num(flags(ma,'unsupported_claims','hybrid_ma'))]]
    add(table(['Measure','Dense-MA','Hybrid-MA'],ma_rows if complete else ma_rows[:3]))
    if not complete:add('Fresh regimen completeness, dose grounding and unsupported-claim assessments are pending. Historical producer safety flags are not copied into those quality fields.')
    add('Reported verifier confidence is an uncalibrated historical self-report. A verified flag may coexist with flagged claims in those traces. Fresh unsupported-claim rate means the fraction of plans with at least one quote-checked finding, not the fraction of all individual claims. Safe withholding and regimen completeness are distinct outcomes. The CSVs retain case-level findings and denominators. No composite difference is assigned to a particular generator, judge or resolver.')
    if complete and analysis:
        add(table(['Saved arm (n=10)','Regimen incomplete','Ungrounded dose','LLM-reported unsupported claim'],[
            [a,num(analysis['safety_all_four_arms'][a]['regimen_incomplete']),
             num(analysis['safety_all_four_arms'][a]['ungrounded_dose']),
             num(analysis['safety_all_four_arms'][a]['unsupported_claim_plan'])]
            for a in ['dense_only','hybrid','dense_only_multiagent','hybrid_multiagent']]))
    if analysis and analysis['suspicious_evaluator_findings']:
        add(f'An automatic evaluator audit flagged {len(analysis["suspicious_evaluator_findings"])} findings that select a heading, an empty quotation or a very short line. These are retained and marked for independent review; line-ID validity alone does not establish a correct claim judgment. Consequently, reported unsupported-claim findings and aggregate ratings carry unresolved evaluator error and cannot certify clinical safety. No unfavorable completed response was discarded or regraded to improve the numerical results.')
    add('## 6. Why the ML score approaches 100%')
    m=evaluation['candidates'][evaluation['selected']]['test']
    add(table(['Supplied-label test measure','Value'],[[k,num(m[k],5)] for k in ['auroc','auprc','accuracy','sensitivity','specificity','brier','f1']]))
    add(f'Thresholded measures in this table use the original validation-selected research cutoff {m["threshold"]:.6f}, not a clinical treatment threshold. At a fixed 0.5 cutoff the same calibrated model has accuracy {audit["model_test_calibrated"]["accuracy_at_0_5"]:.5f}. Different cutoffs explain the two accuracy values; neither establishes prospective clinical performance.')
    demo=audit['demo'];cal=audit['calibration']
    add(f'The pinned 150-tree forest is a concurrent supplied-label classifier using eighteen reviewed inputs and missingness indicators. The days-0-2 test has n={m["n"]}. The synthetic demo\'s raw forest score is {demo["raw_forest_probability"]:.10f}. Calibration applies sigmoid({cal["slope"]:.10f} * logit(raw) + {cal["intercept"]:.10f}), producing {demo["calibrated_supplied_label_probability"]:.12f}. The app\'s >99.9% display is therefore numerical saturation of this dataset model, not diagnostic certainty.')
    add('The raw score is already extreme because the demo follows the dataset\'s strongly separating patterns. Its PCT value of 2 is close to the positive-label fit median of 1.9855, versus 0.31 for negative labels. CRP of 20 is at approximately the 99.34th percentile of all observed fit values. The first, second and third quartiles of the demo\'s reached tree-leaf probabilities are all 1.0. These are dataset associations with undocumented clinical timing/units, not diagnostic likelihoods.')
    add('![Figure 1. Unchanged fitted calibration, internal supplied-label reliability, single-variable separability and synthetic input sensitivity. These diagnostics do not validate clinical EOS risk.](output/research/figures/probability_audit.png)')
    add(table(['Input to fitted calibration','Output dataset score'],[[num(v,6),num(1/(1+math.exp(-(cal['slope']*math.log(v/(1-v))+cal['intercept']))),10)] for v in [.1,.5,.7,.9,demo['raw_forest_probability']]]))
    add(f'Calibration improves the internal Brier score from {audit["model_test_raw"]["brier"]:.5f} to {audit["model_test_calibrated"]["brier"]:.5f}. That assesses the same supplied-label population, not a clinical EOS population. The source has {original["duplicate_patient_hour_rows"]:,} repeated patient/hour rows, {original["conflicting_label_patient_hour_pairs"]:,} conflicting-label patient/hour pairs and {original["inconsistent_baseline_patient_ids"]["Sex"]:,} IDs with changing sex. Birth weight is at its upper recorded value in {original["birth_weight_at_upper_value_fraction"]:.1%} of rows. Its identity, unit, onset and result-availability provenance remain unresolved.')
    add(table(['Diagnostic predictor/feature set','Audit AUC'],[[f,num(audit['single_feature_diagnostics'][f]['test_auroc_oriented_on_fit'])] for f in ['PCT','Oxygen','CRP','Lactate']]+
        [['Baseline-only logistic',num(leak['feature_ablations_logistic']['baseline_only']['test']['auroc'])],['Vitals without laboratory logistic',num(leak['feature_ablations_logistic']['vitals_without_laboratory']['test']['auroc'])]]))
    add('All direct patient-ID and exact predictor-vector overlaps across partitions were zero, fit-only preprocessing was reconstructed, and shuffled-label controls were near chance. The small forest fit-test AUC gap does not suggest ordinary training memorization alone. However, source identities are inconsistent, concurrent laboratory/treatment variables strongly separate the supplied label, and measurement availability relative to diagnosis is unknown. Prospective diagnostic-workflow leakage, label construction artifacts and lack of external validity cannot be ruled out. The training CSV was not confirmed synthetic by the user; only the RAG benchmark was.')
    perturb=demo['measurement_perturbation']
    add(f'In 250 deterministic local measurement perturbations, {perturb["accepted"]} inputs were within development support, {perturb["abstained"]} were withheld and {perturb["invalid_input_rejected"]} were invalid and rejected. Accepted scores remained highly saturated. This is an engineering sensitivity check, not proof of correct risk estimates. Replacing elevated laboratory/vital values changes the score substantially, but these synthetic counterfactuals are not causal treatment effects. Neither arbitrary probability clipping nor relabeling synthetic cases would repair the missing clinical target.')
    add('## 7. Application refinements and corrected development data')
    add('The model endpoint now exposes raw and calibrated scores, calibration parameters and an explicit saturation interpretation; original fitted weights and scores are preserved. Patient-specific retrieval now receives observed symptom/trend queries and allergy/renal-safety queries in addition to broad plan-domain queries. Stored encounter age, gestation and weight reach population filtering. Missing, invalid or future historical timestamps withhold automated synthesis rather than becoming prior observations. Graph and selection modes are propagated rather than reporting only the last query\'s mode. The full development workspace passed 110 backend tests; four demo-only tests are omitted from this public app/research repository. Updated Flutter widgets pass static analysis.')
    add('These later implementation fixes are not credited with the historical pilot scores. Production adapters support pgvector and Neo4j; the local demo uses a local concept-to-passage graph. The pilot CSV arm called Graph is a historical saved ranking, not evidence that a live Neo4j service was benchmarked. Current runtime dose restrictions and dual audits are engineering safeguards, not proof of clinical acceptability.')
    add('For the current thirteen-section care-plan workflow, the model selects immutable recommendation quote IDs. The server displays their actual wording, separately from observed patient measurements and longitudinal summaries, and both auditors check source and patient applicability. This source-selection workflow limits unsupported paraphrase; it does not fill absent evidence or manufacture individualized medication orders.')
    add('The selection prompt now retains full guideline quotes while omitting repeated URLs, filenames and page metadata from the model view; those records remain intact for server-side citations. Patient-state instructions are conditional on recorded findings rather than asserting respiratory illness for every case. The metadata/source-preservation and well-infant regression checks pass. The local demonstration also runs packaged application code inside its container, rather than importing it from a Windows-mounted source tree.')
    add('A later application-source review found two recommendations contaminated by following-section headings. Visual PDF checks corrected only those boundaries, with the original corpus archived and source revision recorded. The no-antibiotic-exposure restriction on NICE 1.5.1 is preserved: that pathway is excluded from the fixed case because treatment status is unknown, and conditional handover uses NICE 1.1.4. The bounded care-plan resolver also selects immutable quote IDs through a compact request, followed by fresh source and safety audits. Regression tests preserve unrecognized clinical notes and conditions. Neither the frozen pilot inputs nor its reported scores are changed by these subsequent fixes.')
    demo_path=OUT/'application_control.json'
    if complete and demo_path.exists():
        control=read(demo_path)
        if control['plan']['verification_status']=='supported_for_review' and all(c.get('completed') and not c.get('reused_completed_draft') for c in control['calls']):
            add(f'A subsequent fixed synthetic application control completed {len(control["calls"])} fresh provider calls and {len(control["verification"]["draft"]["claims"])} source-selected claims. It displayed {len(control["plan"]["plan_sections"])} sections, including {sum(s["status"]=="evidence_supported" for s in control["plan"]["plan_sections"])} supported guidance sections. The source auditor used GPT-OSS-120B and the safety auditor Qwen3.8-27B; the generator shared the source auditor\'s weights. This is a development integration control, separate from the forty historical pilot outputs, not an independent quality or clinical validation study. This preserved first control predates the boundary corrections and does not validate those later changes.')
    add('A separate corrected development set contains 100 synthetic cases and 300 chronological observations across ten template families, with immutable demographics, units, availability times, explicit missing data, gestational-age source scope, renal/allergy/referral scenarios, and no invented EOS outcomes. The original gold was untouched. No new gold care plans were manufactured; independent source mapping is still needed. Template variants are dependent and cannot serve as an external clinical validation cohort.')
    add('## 8. Priorities before expansion')
    add('First, obtain a defensible culture-adjudicated EOS cohort with true birth/onset/result-availability times and verified units; pre-specify calibration and external validation. Keep the current classifier outside clinical decision-making. Second, independently map and review the synthetic benchmark\'s gold passages, references, guideline scope and citation-number provenance, using the corrected cases without rewriting original results. Third, freeze an identical-draft multi-agent ablation and an independent evaluation set, quantify uncertainty and evaluator disagreement, and test workflow integration before a full 100-case quality claim.')
    add('## References')
    for ref in [
        '[1] NICE. Neonatal infection: antibiotics for prevention and treatment, NG195. https://www.nice.org.uk/guidance/ng195',
        '[2] AAP. Management of neonates born at >=35 0/7 weeks with suspected or proven early-onset bacterial sepsis (2018). https://publications.aap.org/pediatrics/article/142/6/e20182894/37522',
        '[3] AAP. Management of neonates born at <=34 6/7 weeks with suspected or proven early-onset bacterial sepsis (2018). https://publications.aap.org/pediatrics/article/142/6/e20182896/37519',
        '[4] WHO. Management of serious bacterial infections in infants aged 0-59 days. https://www.who.int/publications/i/item/9789240102903',
        '[5] Collins et al. TRIPOD+AI. BMJ 385:e078378 (2024). https://www.bmj.com/content/385/bmj-2023-078378',
        '[6] Papineni et al. BLEU (2002); Banerjee and Lavie. METEOR (2005); Zhang et al. BERTScore (2020). Metric package versions and backbone hash are recorded with the reproducible outputs.']:
        add(ref)
    destination=ROOT/('docs/research/phase1_pilot.md' if complete else 'docs/research/phase1_pilot_progress.md');destination.parent.mkdir(exist_ok=True)
    destination.write_text('\n\n'.join(lines)+'\n',encoding='utf8')
    from render_paper import main as render
    render(destination,ROOT/('output/pdf/neoguard-phase1-pilot.pdf' if complete else 'output/pdf/neoguard-phase1-pilot-progress.pdf'),copy_alias=False,include_architecture=False,report_date='26 October 2026',references_new_page=True)
    if complete:(OUT/'decision.json').write_text(json.dumps({'decision':'REVISE','complete':True,'selected_cases':10,'clinical_release_justified':False,
        'metric_pairs':20,'unique_chunk_judgments':206,'plan_judgments':40,'plan_stage_judgments':80,
        'source_id_conflict_groups':8,'selected_source_conflict_ids':3,'selected_cases_without_postnatal_age':10,
        'automatically_flagged_evaluator_findings':len(analysis['suspicious_evaluator_findings']),
        'provider_failures_in_quality_scores':False},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--partial',action='store_true');a=p.parse_args();main(a.partial)
