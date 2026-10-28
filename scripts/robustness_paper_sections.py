"""Measured development addendum; no generated or selectively chosen scores."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/research/rag_development'


def read(name):return json.loads((BASE/name).read_text())
def f(x):return f'{float(x):.4f}'
def interval(a,b):return f'[{f(a)}, {f(b)}]'


def sections():
    audit=read('generalization_audit/summary.json');fresh=read('wording_audit/summary.json')
    repair=read('canonical_router_repair/fresh/summary.json')
    bayes=json.loads((ROOT/'output/research/pic_longitudinal/paper_inspired_bayes/results.json').read_text())
    pilot=read('patient_explanation_v5/summary.json')
    if fresh['completed']!=100 or repair['completed_base_cases']!=100:raise ValueError('Incomplete audit')
    def row(data,g,m,k,metric):return next(r for r in data['statistics'] if (r['guideline'],r['method'],r['depth'],r['metric'])==(g,m,k,metric))
    lines=['### 13.10 Benchmark dependence and wording robustness','',
        'The 100 exposed synthetic base cases contain only '+str(sum(audit['unique_focused_queries'].values()))+
        ' distinct focused question templates: NICE 12, AAP 6 and WHO 6. Parameter variants do not establish '
        'independent clinical reasoning coverage. Renaming all passage identifiers and graph endpoints '
        f'preserves rankings for {audit["identifier_invariance_passes"]}/100 cases; this excludes literal '
        'identifier dependence in this check but does not exclude conceptual or benchmark overfitting. '
        'A query-agnostic publisher-summary ordering and 1,000 within-source gold permutations are '
        'reported as diagnostics, not clinical retrieval performance. The query-agnostic WHO MRR@4 is '
        '0.9167 compared with contextual MRR@4 of 0.8667, indicating that common summary passages and '
        'coarse relevance sets can inflate apparent ranking success.','',
        'Two deterministic wording-transform slots per base case preserve standalone numeric values and explicit '
        'negation/unknown markers. Of 200 slots, 152 change the focused wording and 48 are identical controls '
        '(NICE 13, AAP 5 and WHO 30); these slots are not independent additional cases. Clinical equivalence remains unreviewed. The fresh stress test reruns '
        'both pinned cross encoders on changed questions, with RRF k=60 and bounded MMR diversity 0.15. '
        'The fixed-facet arm explicitly retains earlier facet questions; a separate question-only arm '
        'omits those facets. Original-wording replay matches the previous pipeline for '
        f'{fresh["original_replay_matches"]}/100 cases. Neither arm is a fresh LLM-planned final evaluation '
        'or an independent patient cohort. Complete source-separated R/P/MRR/nDCG at 4 and 8, paired '
        'case-level and scenario-family 95% intervals from 2,000 resamples, and query-only negatives '
        'are retained in CSV. No new Groq calls are used for these retrieval checks.','',
        'Bounded terminology normalization is added to the intent selector after observing the wording '
        'failure. Original clinical questions, patient facts, units, negation and indexed source text '
        'are preserved. This is a post-hoc development repair, not independent validation.','',
        'Table 34. Fresh fixed-facet wording stress and post-hoc routing repair. Each NICE row covers '
        '40/40 cases; each AAP or WHO row covers 30/30. Coverage denotes retrieval completion, not released '
        'clinical answers. P@8 has annotation ceilings of 0.3344, 0.2500 and 0.2500 for NICE, AAP and WHO; '
        'raw precision is not rescaled. Supplemental definitions are outside the eight recommendation slots.','',
        '| Guideline | Wording / selector | R@4 | MRR@4 | R@8 | P@8 | nDCG@8 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for g in ['NICE','AAP','WHO']:
        for label,data,method in [('Original / legacy',fresh,'fixed_facet_plan:original'),
                                  ('Plain / legacy',fresh,'fixed_facet_plan:plain_language'),
                                  ('Plain / canonical',repair,'fixed_facet_plan:canonical_v2:plain_language')]:
            values=[row(data,g,method,k,metric)['mean'] for k,metric in [(4,'recall'),(4,'mrr'),(8,'recall'),(8,'precision'),(8,'ndcg')]]
            lines.append('| '+g+' | '+label+' | '+' | '.join(f(v) for v in values)+' |')
    lines+=['','Table 35. Paired plain-minus-original Recall@4 differences before repair. The same '
        '100 base cases are used; family bootstrap has only six scenario families per source.','',
        '| Guideline | Difference | Case 95% CI | Family 95% CI |',
        '| --- | --- | --- | --- |']
    paired=list(csv.DictReader((BASE/'wording_audit/paired_differences.csv').open()))
    for g in ['NICE','AAP','WHO']:
        r=next(r for r in paired if (r['guideline'],r['method'],r['depth'],r['metric'])==(g,'fixed_facet_plan:plain_language','4','recall'))
        lines.append(f'| {g} | {f(r["mean"])} | {interval(r["case_low"],r["case_high"])} | {interval(r["family_low"],r["family_high"])} |')
    lines+=['','The original NICE Recall@4 of 0.9167 becomes 0.7667 under plain wording; the original '
        'AAP Recall@4 and MRR@4 of 1.0000 become 0.8333 and 0.6667 before repair. The canonical selector '
        'restores AAP plain Recall@4 to 1.0000 and MRR@4 to 0.9167, while NICE plain Recall@4 remains '
        '0.7667. Aggregate original-wording retrieval targets therefore do not establish robustness. '
        'A locked, independently authored clinical challenge set and adjudicated relevance labels '
        'remain necessary; further adaptation to these exposed variants cannot supply independent evidence.','',
        '### 13.11 Patient-specific explanation safety smoke test','',
        f'Three of {pilot["planned"]} planned development cases are attempted, one each from NICE, AAP and '
        f'WHO. All {pilot["quality_completed"]} attempts complete without an unresolved provider failure. '
        f'The structural checks accept {pilot["structurally_valid"]}/3 drafts; complete two-model audits '
        f'occur for {pilot["complete_audits"]}/3, and {pilot["whole_draft_released"]}/3 is released by the '
        'research graph. Attempted release coverage is 1/3 (0.3333), with planned-population coverage '
        '1/18 (0.0556); the other 15 cases are unattempted, not quality failures. No alignment metric '
        'or clinical utility score is inferred from these counts. Completed failures remain saved.','',
        'The NICE draft incorrectly treats unclear initial suspicion as satisfying a reassuring '
        'stopping condition and adds unsupported treatment escalation. It is withheld before semantic '
        'auditing because a numerical-unit guard rejects another claim; this is not evidence that '
        'semantic auditors detected its clinical errors. The WHO evidence auditor rejects conflation '
        'of all PSBI signs with the narrower clinical-severe-infection category, whereas the safety '
        'auditor accepts the draft. The AAP draft passes both auditors, yet its action prose omits the '
        'site-specific-infection exception present in its cited stopping recommendation. These are '
        'engineering source-comparison findings awaiting clinician adjudication, not a clinical error '
        'rate. Separate prompts using the same model backbone are not independent clinical assessors.','',
        'A constrained evidence-brief research fallback renders unchanged recorded findings and unknowns '
        'separately from complete indexed passages. Exact text/hash checks preserve every condition and '
        'exception in the selected source units, and chronological-history checks reject future records. '
        'No free-form model statement or patient treatment eligibility is released by this fallback. '
        'Source fidelity is an engineering property and does not establish relevance, sufficient context '
        'or clinical usefulness. The fallback is not presented as a fully working care-plan generator. '
        'The prototype is not integrated into the clinical app. Final evaluation, candidate app '
        'integration and publication push remain on hold.','',
        '### 13.12 Paper-inspired Bayesian longitudinal comparison','',
        'Nguyen et al. [19] use the same PIC database for a different task: sepsis diagnosis in 3,014 '
        'paediatric admissions, including 134 sepsis admissions, using first-24-hour clinical and '
        'laboratory information. Their best full-information TAN AUROC is 0.866 (95% CI 0.826–0.906), '
        'with sensitivity 0.463, specificity 0.949 and accuracy 0.930. The under-30-day subgroup AUROC '
        'is 0.783 (95% CI 0.716–0.850), with sensitivity 0.338; that subgroup is still not an EOS '
        'pre-culture forecasting cohort. A constant-negative classifier has accuracy 2880/3014 '
        '(0.9555) in the reported overall cohort, illustrating why accuracy alone is unsuitable. '
        'The reported admission-level cross-validation does not establish patient-disjoint grouping '
        'from the available description. Actual leakage in that study is not asserted.','',
        'The transferable ideas are conditional-dependence modelling, explicit missingness, '
        'clinician-informed feature selection and comparison with simpler probabilistic baselines. '
        'Culture and retrospectively available first-day laboratory values are not imported as '
        'pre-culture predictors. A smoothed discrete naive Bayes and tree-augmented naive Bayes (TAN) '
        '[20] are implemented for snapshot and actual-time longitudinal features. Discretization, '
        'variable selection, priors, conditional probabilities and TAN structure are learned only '
        'within each training fold. Missing values occupy an explicit state, which can encode '
        'recording practices and is not an imputed normal measurement. Equal total infant weights '
        'and three patient-disjoint folds are retained. Seeds 31, 47 and 83 and smoothing equivalent '
        'sample size 10 are declared before these runs. All 12 comparisons remain reported; the '
        'cohort remains 543 infants with seven positive infants and 1,436 landmarks.','',
        'Table 36. Paper-inspired Bayesian development results; no held-out patient row is used for '
        'fitting its fold model. Seed-31 patient-bootstrap intervals and paired comparisons versus '
        'the prior snapshot logistic model are in CSV; no seed is selected for deployment.','',
        '| Method | Seed | AUROC | AUPRC | Brier |',
        '| --- | --- | --- | --- | --- |']
    for r in bayes['results']:
        lines.append(f'| {r["method"].replace("_"," ")} | {r["seed"]} | {f(r["auroc"])} | {f(r["auprc"])} | {f(r["brier"])} |')
    ci=next(r for r in bayes['intervals'] if r['method']=='snapshot_tan' and r['metric']=='auroc')
    lines+=['','Snapshot TAN at seed 31 has AUROC 0.5750 with patient-bootstrap 95% CI '+
        interval(ci['lower_95'],ci['upper_95'])+
        '. Longitudinal TAN has AUROC 0.4033, 0.4310 and 0.4535 at the three declared seeds. These '
        'results do not establish adequate discrimination, calibration or superiority to earlier '
        'candidates. Large individual posterior scores remain uncalibrated research outputs; neither '
        'architectural complexity nor a favourable seed justifies a clinical EOS probability. '
        'A larger linked maternal-neonatal cohort with timestamped result availability and adjudicated '
        'early-onset outcomes is required. No new Bayesian model is installed as an app predictor.','']
    nested=ROOT/'output/research/pic_longitudinal/nested_improvement/results.json'
    if nested.exists():
        study=json.loads(nested.read_text())
        influence=json.loads(nested.with_name('positive_event_influence.json').read_text())
        lines+=['### 13.13 Nested imputation and model-selection experiment','',
            'Eight additional fixed candidates compare compact temporal features, median versus '
            'distance-weighted five-neighbour imputation, regularized logistic regression, forests, '
            'Extra Trees and native-missingness gradient boosting. The unchanged cohort contains 543 '
            'infants, seven positive infants and 1,436 landmarks. Three outer patient-separated folds '
            'contain two inner folds for candidate selection by patient-weighted AUPRC. Feature '
            'selection, scaling, imputation donors and estimators are fitted within each training '
            'fold. Observed-feature eligibility requires five distinct infants. All seeds 31, 47 '
            'and 83 and all candidate scores are retained; no favourable outer result is selected '
            'for deployment. The already exposed cohort remains development data, despite nested selection.','',
            'Table 37. Nested selection and KNN-imputation candidate results; 543/543 infants and '
            '1,436/1,436 landmarks scored for every row. This is prediction coverage, not clinical '
            'validation or generated-answer release coverage.','',
            '| Method | Seed | AUROC | AUPRC | Brier |',
            '| --- | --- | --- | --- | --- |']
        for r in study['metrics']:
            if r['method'] in ['nested_selected','compact_lr_knn_C01']:
                lines.append(f'| {r["method"].replace("_"," ")} | {r["seed"]} | {f(r["auroc"])} | {f(r["auprc"])} | {f(r["brier"])} |')
        ci=next(r for r in study['intervals'] if r['method']=='nested_selected' and r['metric']=='auroc')
        knn=next(r for r in influence if r['method']=='compact_lr_knn_C01')
        lines+=['','Primary-seed nested-selected AUROC has an infant-bootstrap 95% interval of '+
            interval(ci['low_95'],ci['high_95'])+
            '. The KNN AUPRC increase at seed 31 does not persist at the other two declared seeds. '
            'Omitting one positive infant from fixed seed-31 KNN predictions gives AUPRC values ranging '
            'from '+f(knn['min_auprc_after_omission'])+' to '+f(knn['max_auprc_after_omission'])+
            '; this is a fixed-prediction influence diagnostic, not a retrained leave-one-out study. '
            'A reliable performance improvement is not established. No new PIC predictor is promoted '
            'to the application. Missing maternal predictors are not invented, and laboratory results '
            'without verified availability timestamps remain excluded.','']
    new_cohorts=ROOT/'output/research/new_neonatal_cohorts/results.json'
    if new_cohorts.exists():
        study=json.loads(new_cohorts.read_text())
        lines+=['### 13.14 Separate preterm biomarker and neonatal bloodstream-infection studies','',
            'Two newly supplied real-data cohorts are evaluated separately. The workbook [21] contains '
            '138 preterm infants, 69 culture-proven cases and 69 controls. Its file checksum matches '
            'the public Figshare record. Twelve maternal/perinatal and blood-count features are retained; '
            'the exact outcome-copy SEPSIS SIGNS, identifiers, duplicate categories and six redundant '
            'derived indices are excluded. Gestation uses weeks plus days/7. Extreme source counts '
            'are not silently corrected; selected counts use log1p. Individual onset and availability '
            'times are unavailable, so EOS-only and longitudinal forecasting claims cannot be established.','',
            'The CHOP registry [22] supplies 580 eligible evaluations in 472 infants aged under 28 days, '
            'with 53 bacteremic evaluations in 52 infants. Bacteremia is compared with the registry '
            'rule-out group; other outcome categories and non-blood-culture-positive cases are excluded. '
            'Fourteen demographic and at/before-evaluation features are retained. Culture/outcome '
            'fields, IDs, treatment timing, future support-free days, length of stay and calendar-day '
            'maximum temperature are excluded. Only one bacteremic infant appears in the recorded '
            'age-0–2-day subset, precluding meaningful EOS training there. The companion R scripts '
            'contain no additional cohort or raw longitudinal measurements.','',
            'Both comparisons use five outer patient-separated folds and three inner folds. Five '
            'fixed candidates compare regularized logistic regression, Random Forest, Extra Trees '
            'and shallow gradient boosting. Model selection maximizes inner AUROC; thresholds maximize '
            'inner balanced accuracy over a fixed 0.05–0.95 grid. Training-fold median imputation, '
            'missing indicators and scaling are fitted without outer-test patients. Each infant '
            'has equal total loss/evaluation weight. All seeds 31, 47 and 83 and fixed-candidate '
            'results are retained, with demographic-only controls.','',
            'Table 38. Primary-seed nested-selected diagnostic development results. All 138/138 '
            'workbook infants and 580/580 CHOP episodes are scored. CHOP episodes remain grouped by '
            'infant. Percentages use fold-specific inner-selected thresholds, not a threshold '
            'optimized on outer outcomes; these are not clinical action thresholds.','',
            '| Dataset | AUROC [95% CI] | Accuracy | Sensitivity | Specificity | Precision |',
            '| --- | --- | --- | --- | --- | --- |']
        for dataset in ['workbook','chop']:
            r=next(r for r in study['metrics'] if (r['dataset'],r['seed'],r['method'])==(dataset,31,'nested_selected'))
            ci=next(r for r in study['intervals'] if (r['dataset'],r['method'],r['metric'])==(dataset,'nested_selected','auroc'))
            lines.append('| '+dataset+' | '+f(r['auroc'])+' '+interval(ci['low_95'],ci['high_95'])+' | '+' | '.join(f'{100*r[k]:.2f}%' for k in ['accuracy','sensitivity','specificity','precision'])+' |')
        lines+=['','Confidence intervals use 2,000 infant-level resamples of fixed out-of-fold predictions; '
            'they do not include all refitting, phenotype and external-transport uncertainty. The '
            'primary-seed paired AUROC difference against demographics is +0.0373 (95% CI '
            '[-0.0177, +0.0910]) for the workbook and +0.0525 [0.0021, 0.1058] for CHOP. Workbook '
            'demographic baselines are higher at seeds 47 and 83; added blood-count value is therefore '
            'not consistently established. CHOP has an internal discrimination gain in the primary '
            'comparison, while low specificity and precision remain material limitations.','',
            'These results show more encouraging discrimination than the earlier PIC comparisons on '
            'different cohorts and targets; they do not establish improvement of the PIC EOS forecasting '
            'model. The selected 50:50 preterm sample cannot establish population prevalence, predictive '
            'values at routine EOS prevalence or calibrated absolute EOS probabilities. CHOP is '
            'conditioned on sepsis evaluation and a treatment-duration-informed rule-out phenotype; '
            'evaluation-time support can reflect an already ill infant. Neither study supplies raw '
            'serial histories or the required linked maternal infection/antibiotic factors. No model '
            'is promoted to the app; independent clinical/external validation remains unavailable.','']
    bmj=ROOT/'output/research/bmj_boruta_adaptation/results.json'
    if bmj.exists():
        study=json.loads(bmj.read_text())
        lines+=['### 13.15 BMJ paper-inspired Boruta and sensitivity-first forest comparison','',
            'Kainth et al. [23] report a Boruta/Random Forest EOS model developed on 2,924 neonates '
            'with 548 culture-positive outcomes, with a separate 147-neonate validation cohort. Their '
            'public repository provides training code but no supplied fitted model or original study '
            'cohort. The local comparison therefore adapts the approach to available features rather '
            'than reproducing the published model or externally validating its weights. Original '
            'maternal/clinical, centre and pre-suspicion device-exposure inputs are not fabricated.','',
            'The adaptation uses BorutaPy 0.4.3 with 1,000 shallow selection trees and a 30-iteration '
            'cap, one latest training observation per infant, and training-only absolute Pearson '
            'correlation pruning above 0.7. This differs from R Boruta; repository calls also specify '
            '10,000 trees and 2,000 runs, whereas the paper prose describes 1,000 trees. Final forests '
            'use 120 trees, maximum depth 8 and up to five split candidates. Training-only class-balanced '
            'infant-normalized loss weights replace ROSE oversampling, preserving mixed Kaggle labels '
            'without inventing an infant-level outcome. All-feature unbalanced and balanced forests '
            'are controls. Three forest seeds share fixed patient splits and one selector per fit fold; '
            'this is forest-randomization stability, not independent clinical replication.','',
            'Kaggle retains the original patient-disjoint fit, threshold and test partitions, leaving '
            'the original calibration partition unused. PIC retains three original patient-level outer '
            'folds, reserving threshold-selection infants within each outer training fold. Only three '
            'or four positive infants remain for fitting and one positive infant per threshold set. '
            'Thresholds maximize specificity while attaining at least 90% sensitivity on threshold '
            'patients only; held-out outcomes never select or revise the threshold.','',
            'Table 39. Primary forest-seed results. Kaggle covers 1,598/1,598 test observations in 509 '
            'IDs; PIC covers 1,436/1,436 landmarks in 543 infants. Each infant has equal total metric '
            'weight, unlike historical row-unweighted Kaggle tables. The 90% threshold-set sensitivity '
            'target does not imply 90% sensitivity on held-out infants.','',
            '| Dataset / arm | AUROC | Accuracy | Sensitivity | Specificity | Precision |',
            '| --- | --- | --- | --- | --- | --- |']
        for r in study['metrics']:
            if r['seed']==31:
                lines.append('| '+r['dataset']+' / '+r['arm'].replace('_',' ')+' | '+f(r['auroc'])+' | '+' | '.join('undefined' if r[k] is None else f'{100*r[k]:.2f}%' for k in ['accuracy','sensitivity','specificity','precision'])+' |')
        lines+=['','PIC Boruta retains three, two and one features across fit folds, with age and '
            'observation recency selected in the first fold. Such recording-process signals and small '
            'event counts limit biological interpretation. Its AUROC is 0.4580 (infant-bootstrap 95% CI '
            '[0.3821, 0.5489]) and held-out sensitivity is 0.7143, below the target. The paired AUROC '
            'difference versus the all-feature balanced forest has 95% interval [-0.3383, 0.0633]; '
            'superiority is not established. Kaggle Boruta AUROC is 0.9975 [0.9960, 0.9986], with a '
            'paired difference interval [-0.0037, -0.0012] versus the balanced forest. Its held-out '
            'sensitivity remains below 90% across all three forest seeds. These exposed-case internal '
            'results do not improve source label provenance or establish clinical EOS reliability. '
            'Thresholds are not retuned on these test failures. No candidate replaces the app model.','']
    return '\n'.join(lines)
