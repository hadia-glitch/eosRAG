"""Insert the completed, measured pilot into the full research manuscript."""
import csv,json
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/research/phase1_pilot'

def rows(name):
    with (OUT/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def table(headers,body):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(map(str,r))+' |' for r in body])
def avg(rs,arm,key):return mean(float(r[key]) for r in rs if r['arm']==arm)

def main():
    progress=json.loads((OUT/'progress.json').read_text())
    if not progress['complete']:raise RuntimeError('Do not publish an incomplete pilot as final research.')
    analysis=json.loads((OUT/'analysis.json').read_text())
    exact=rows('01_pilot_exact_retrieval.csv');sem=rows('03_pilot_semantic_summary.csv')
    usability=rows('04_pilot_clinical_usability.csv');gen=rows('05_pilot_generation.csv')
    lines=[];add=lines.append
    add('## 12. Frozen ten-case pilot and saturated-score investigation')
    add('### 12.1 Protocol and provenance')
    add('A subsequent Phase 1 pilot analyzes ten cases from a separately supplied synthetic 100-case care-plan benchmark. Eligibility requires all five historical retrieval arms and all four saved plan arms. Deterministic metadata coverage selects four NICE, three AAP and three WHO cases from thirty eligible cases without inspecting outcomes. The original gold is preserved; twelve selected historical rows disagree with the canonical JSON gold. Every selected top-ten and gold ID resolves in the benchmark-declared 489-passage corpus. The exact cases, source hashes and discrepancies are available in the pilot manifest. This pilot evaluates saved outputs, not the later application refinements.')
    add('All ten selected original cases omit postnatal age. EOS eligibility and age-specific treatment conditions therefore cannot be confirmed. This fact remains unknown in the fresh prompts; corrected development-case facts are never substituted. A high automated clinical rating cannot establish that the missing eligibility conditions were met.')
    add('The 489 corpus rows have 481 distinct IDs: eight identifiers map to conflicting texts. Three colliding IDs affect selected AAP cases 003, 007 and 011. The frozen dictionary used the last CSV occurrence; a separate audit verifies this and preserves every variant. Exact-ID metrics cannot resolve content identity, and semantic/source scores are conditional on these frozen texts. This source ambiguity was not repaired by altering original gold or substituting favorable passages.')
    add('Exact MRR@10 and gold-normalized binary NDCG@10 use the actual first ten retrieved IDs, excluding expanded context. Fifty NDCG values independently match scikit-learn within 1e-12. Fresh GPT-OSS-120B judgments cover 206 unique case/passage pairs; opaque aliases hide arms. Relevance grades are 0-3 and useful precision uses grade >=2. Semantic NDCG uses gains 2^grade-1 and a shared ideal from each case\'s judged five-arm union, not a corpus-wide ideal. Four grade/applicability/usefulness inconsistencies are retained. Dense and Vector are historical labels; their implementation distinction and controlled ablation provenance cannot be established from the CSVs.')
    add('### 12.2 Exact and semantic retrieval')
    add(table(['Arm','Exact MRR@10','Exact NDCG@10','Useful P@10','Semantic MRR@10','Semantic NDCG@10'],[
        [a.title(),f'{avg(exact,a,"exact_mrr_at10"):.4f}',f'{avg(exact,a,"exact_ndcg_at10"):.4f}',
         *[f'{avg(sem,a,k):.4f}' for k in ['utility_precision_at10','semantic_mrr_at10','semantic_ndcg_at10']]]
        for a in ['dense','sparse','vector','graph','hybrid']]))
    ci=analysis['paired_comparisons']['retrieval_exact_ndcg_at10'];lo,hi=ci['bootstrap_percentile_95']
    add(f'Graph ranks the first canonical hit most effectively; Hybrid has the highest exact and semantic NDCG, and both tie on useful precision. Hybrid minus Dense exact NDCG is {ci["mean_difference"]:.4f}, with a descriptive paired case-bootstrap 95% percentile interval [{lo:.4f}, {hi:.4f}] (20,000 resamples, seed 20261025). Template/source dependence limits interpretation. Exact and semantic arm-mean NDCG rank correlation is {analysis["exact_versus_semantic_ndcg_arm_rank_spearman"]:.2f}. A historical Graph ranking does not establish that a live Neo4j service was benchmarked.')
    add('### 12.3 Source-separated plan assessment')
    add('Each of forty saved outputs receives two fresh rubric-4 passes: grounding/citation assessment sees only that plan\'s retrieved evidence, while clinical usefulness/completeness sees case facts and wider guideline evidence. All eighty stage responses are retained. Findings select immutable candidate-line IDs, materialized locally as exact quotations; omissions are separate. Earlier exploratory rubrics exposed dose-omission and gold/context confusion and are archived outside final scores. MA traces do not establish E-number mapping, which the evaluator must not invent. These automated ratings are fallible proxies. Different saved generations prevent causal attribution to verification agents.')
    add(table(['LLM rating (1-5)','Dense','Hybrid'],[
        [k.replace('_',' ').title(),f'{avg(usability,"dense",k):.3f}',f'{avg(usability,"hybrid",k):.3f}']
        for k in ['faithfulness','citation_correctness','citation_completeness','clinical_correctness','clinical_completeness','clinical_utility','safety']]))
    add(table(['Saved arm (n=10)','Regimen incomplete','Ungrounded dose','LLM-reported unsupported-claim plan'],[
        [a,*[f'{analysis["safety_all_four_arms"][a][k]:.3f}' for k in ['regimen_incomplete','ungrounded_dose','unsupported_claim_plan']]]
        for a in ['dense_only','hybrid','dense_only_multiagent','hybrid_multiagent']]))
    add(f'The evaluator-quality audit flags {len(analysis["suspicious_evaluator_findings"])} heading/empty/very-short-line findings for independent review. They remain in the raw ratings and rates rather than being deleted or regraded. Thus these findings cannot certify safety or support a precise hallucination-reduction claim. Regimen completeness and safe withholding are separate. Full case-level findings and denominators accompany the seven numbered CSVs.')
    add(table(['Fresh similarity metric','Dense','Hybrid'],[
        [k,f'{avg(gen,"dense",k):.4f}',f'{avg(gen,"hybrid",k):.4f}'] for k in ['bleu','meteor','bertscore_f1','anchor_grounding_recall']]))
    add('The references are historical deterministic templates, not independent clinical gold. BLEU is sentence BLEU-4/100 with 13a tokenization and exponential smoothing. METEOR uses lowercased WordPunct tokens and Porter/WordNet matching. DistilBERT BERTScore uses layer 5 without IDF or baseline rescaling; fourteen of twenty pairs exceed its standard 512-token window. Full plans are still used by the usability judge. Fresh ROUGE-L F1 is 0.3258 for Dense and 0.3167 for Hybrid. Similarity does not establish correct care. The separate metric environment and backbone hash are recorded in generation_metrics.json; they do not replace versions from the earlier experiment.')
    add('### 12.4 Why the demonstration score exceeded 99.9%')
    add('The pinned days-0-2 forest returns raw score 0.9982920927203368. Its fitted calibration applies sigmoid(3.267761146142852 * logit(raw) + 0.9684784989483102), producing 0.9999999996547169. Internal Brier improves from 0.01817 to 0.00938 on the supplied labels. This numerical sharpening explains the display, but does not calibrate clinical EOS risk. PCT alone yields oriented test AUC 0.98599, oxygen 0.96877 and CRP 0.95427; these associations and unresolved timing/identity defects raise source-label and workflow-leakage questions. A small fit-test gap is insufficient reassurance. The training CSV was not confirmed synthetic; only the RAG benchmark was.')
    add('Before calibration, the demo already closely matches strongly separating dataset patterns: PCT=2 is near the positive-label fit median 1.9855, compared with negative-label median 0.31; CRP=20 is at the 99.34th fit percentile. The reached tree-leaf probability quartiles are all 1.0. These explain model saturation statistically without establishing a clinical diagnosis or validating the dataset\'s measurement units.')
    add('![Figure 4. Probability audit of the unchanged fitted model: calibration, internal reliability, single-variable label separation and non-causal input sensitivity.](output/research/figures/probability_audit.png)')
    add('Across 250 deterministic local measurement perturbations, 153 are within support, 94 are withheld and three invalid inputs are rejected. Accepted scores remain saturated. Replacing the elevated laboratory values alone changes the demo score to 0.61025; replacing vital signs alone gives 0.89437; replacing both gives 0.00004782. These are sensitivity diagnostics, not causal treatment effects or external validation. No arbitrary clipping or synthetic outcome relabeling is used to manufacture plausible risk.')
    add('### 12.5 Refinement and decision')
    add('The application now exposes raw/calibrated scores and a saturation interpretation. Previously unused patient-context queries now reach plan retrieval, along with allergy/renal/history queries. Stored encounter age, gestation and weight reach population filtering. Missing, future or invalid historical timestamps withhold automated synthesis. Graph and diversity modes propagate across domain queries. All 110 backend tests pass and the updated Flutter widgets pass static analysis. These changes are subsequent engineering refinements and are not credited with the historical scores.')
    add('The current thirteen-section review workflow selects immutable guideline recommendation IDs and materializes actual source wording, while displaying patient observations and longitudinal summaries separately. Both audit roles check the selected claims. This reduces quotation/paraphrase defects but does not create missing evidence, dosing authority or an individualized medication order.')
    add('The selection model view omits repeated file/URL/page metadata while retaining every actual quote, source, version and section; original citation records remain intact on the server. Patient-state instructions are conditional on recorded findings, with a regression check against inventing respiratory illness for a well infant. The local demo now uses packaged container code rather than a Windows-mounted source tree. These are subsequent runtime refinements, not retrospective changes to pilot scores.')
    add('Subsequent visual PDF checks found two application passages with trailing headings from the next section. Only those verified extraction boundaries were corrected, preserving the original application corpus and a versioned change record. NICE 1.5.1 applies to babies who have not received antibiotics; it is excluded from this fixed case with unknown treatment status. Conditional future handover instead uses NICE 1.1.4. The care-plan resolution request now selects immutable quote IDs without duplicating full previous passages and citation metadata; both auditors must freshly recheck the revision. Tests retain source conditions and unrelated clinical notes. These fixes do not alter frozen pilot sources, gold or scores.')
    control_path=OUT/'application_control.json'
    control=json.loads(control_path.read_text()) if control_path.exists() else None
    if control and control['plan']['verification_status']=='supported_for_review' and all(c.get('completed') and not c.get('reused_completed_draft') for c in control['calls']):
        add(f'A subsequent fixed synthetic application control completed three fresh provider calls, generating {len(control["verification"]["draft"]["claims"])} source-selected claims and displaying thirteen sections, nine with supported guidance. GPT-OSS-120B performed generation/source review and Qwen3.8-27B performed safety review. This integration control is separate from the historical pilot and does not change its scores or establish independent clinical quality. The preserved first control predates the boundary corrections and does not validate those later changes.')
    add('A separate corrected development set contains one hundred cases and three hundred chronological observations across ten template families, with immutable demographics, explicit units/availability/unknowns and gestation-specific guideline scope. It contains no invented EOS labels or newly manufactured gold care plans; it does not replace the original pilot. Template variants are dependent and need independent source mapping.')
    add('The pilot decision is REVISE. First establish a defensible culture-adjudicated, time-aware EOS cohort and external calibration. Second independently review benchmark gold, source scope, references and citation provenance. Third freeze an identical-draft verification ablation and independent evaluation set, with evaluator-disagreement and workflow checks. Provider execution failures remain operational logs outside all quality means. The present research artifact does not justify clinical release.')
    target=ROOT/'docs/research/manuscript.md';text=target.read_text(encoding='utf8')
    before,refs=text.split('## References',1)
    before=before.split('## 12. Frozen ten-case pilot',1)[0].rstrip()
    target.write_text(before+'\n\n'+'\n\n'.join(lines)+'\n\n## References'+refs,encoding='utf8')
    print('Integrated complete pilot into '+str(target))

if __name__=='__main__':main()
