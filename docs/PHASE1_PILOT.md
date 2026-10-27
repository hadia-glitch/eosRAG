# Phase 1 pilot protocol and calibration investigation

The supplied Phase 1 protocol is executed in `output/research/phase1_pilot/`.
Exactly seven numbered CSV result files are produced. JSON files retain input
hashes, selected cases, prompts, raw model responses, case-level semantic scores,
metric configuration and completion status. Provider failures are operational
records under `output/operational/phase1_pilot/`, outside quality populations.

## Frozen original pilot

The canonical source is the supplied 100-case benchmark in Downloads. The user
confirmed that this RAG benchmark is synthetic; this confirmation does not apply
to the training CSV. Ten cases are selected from the 30 cases having all five
retrieval arms and all four saved plan/MA outputs. Selection uses metadata only,
with NICE/WHO/AAP quotas of 4/3/3 and coverage of risk, contraindications, trends
and ambiguity. Case-ID order breaks ties. No observed metric enters selection.
The original gold evidence is never repaired or replaced in the pilot.

Twelve selected historical rows have gold-ID sets differing from the canonical
100-case JSON. All differences are retained in the manifest. The corpus is the
benchmark-declared `chunks_ingested.csv`; every selected top-10 and gold ID is
present. That establishes ID/text availability, not clinical validity of gold.

The 489 CSV rows have 481 distinct IDs and eight conflicting-text ID groups.
Three such IDs affect the selected AAP cases 003, 007 and 011. The frozen input
dictionary used the last CSV occurrence; `source_id_collision_audit.json`
independently verifies that mapping and preserves all variants. Exact-ID scores
cannot disambiguate passage identity, and semantic/source scores are conditional
on those frozen texts. No source/gold is silently repaired after scoring.

Exact NDCG uses binary relevance and ideal DCG from all canonical gold IDs,
truncated to rank ten. Missing ranks receive zero relevance and repeated IDs do
not receive duplicate gain. All fifty values were independently checked against
scikit-learn, with a maximum difference below 1e-12. Anchor recall is normalized
exact phrase coverage in actual top-10 text or actual generated plan text, as
appropriate. Expanded context is excluded from strict retrieval scores.

Fresh chunk judging uses GPT-OSS-120B, temperature zero, with actual passages,
the case, active guideline and gold evidence. Opaque aliases hide arm labels.
Each case/passage pair is judged once and reused across arms only within that
same fresh assessment. Utility is defined by grade >=2, as requested. Any
disagreement between grade, applicability or the model's separate usefulness
boolean is retained in the raw trace and counted in progress metadata.

Semantic NDCG uses graded gain (2^grade - 1). Its shared ideal ranking is the
judged union of the five arms' top-10 passages for that case. This is a pooled
judgment, not a corpus-wide ideal or semantic recall measurement. Only cases
with every union passage judged enter paired arm summaries.

Plan judging is **LLM-based clinical usability assessment - not clinician
validation**. Two initial exploratory plan judgments exposed confusion between
an omitted dose and an unsupported assertion. They remain saved but are excluded
from the final analysis. A rubric-2 free-text quote also failed exact matching.
An exploratory combined-context judgment also confused gold with actual retrieved
evidence. Final rubric 4 therefore separates a grounding pass (only retrieved
plan evidence) from a clinical-usefulness pass (case and wider guideline text).
Both select immutable candidate line IDs and keep omissions separate. Exact
quotations are materialized deterministically from the actual plan text.
Actual retrieved context determines faithfulness; gold passages do not become
retroactive plan citations. Numbered E-citation mapping is unavailable in the
saved MA traces and is explicitly disclosed rather than inferred from ID order.

The five historical arm names are used exactly as supplied. Their CSVs do not
fully establish the implementation distinction between "Dense" and "Vector",
or prove a controlled retriever ablation. Scores describe the saved rankings;
they are not measurements of the subsequently updated application code.

Historical Dense/Hybrid/MA outputs are different saved generations, not the same
draft with a controlled verification toggle. Differences therefore describe a
composite historical pipeline comparison, not causal effects of individual
agents or measurements of the subsequently changed application.

All ten selected original cases omit postnatal age. The evaluator receives this
as unknown; EOS eligibility and age-specific recommendations cannot be confirmed.
The independent corrected cases do not backfill those missing facts. An automated
audit additionally flags heading/empty/short-line claim findings for independent
review, retaining the original scores rather than silently removing unfavorable
findings. This records evaluator limitations as well as pipeline limitations.

BLEU-4, METEOR, ROUGE-L and DistilBERT BERTScore are freshly recomputed from saved
plans and frozen references. BERTScore uses layer 5, no IDF or baseline rescaling;
14/20 pairs exceed its standard 512-token limit. Full texts remain available to
the plan judge. Template similarity is not a clinical correctness measure.

## Model probability audit

`output/research/probability_audit/audit.json` contains a fresh audit of the pinned
days-0-2 forest. The previously reported test partition remains a post-hoc audit
set, not a newly untouched validation cohort. The demonstration's raw forest
score is 0.9982920927203368. Calibration applies
`sigmoid(3.267761146142852 * logit(raw) + 0.9684784989483102)`, yielding
0.9999999996547169. No probability was clipped to make the result look plausible.

The app now exposes the raw score, calibrated dataset score and saturation
warning. This model classifies an unadjudicated concurrent supplied label. It
does not establish culture-confirmed EOS, prospective lead time, transportability
or calibrated clinical risk. The source CSV's identity conflicts, missing
availability timestamps and undocumented units remain unresolved. Synthetic
RAG cases cannot repair those training-data defects.

## Corrected development cases

`data/synthetic_eos_v2/cases.json` is a separately authored set of 100 cases,
containing 300 time-ordered observations across ten template families. It records
measurement units, known/unknown facts, timing, allergy/renal/referral context and
gestational-age-specific AAP scope. No EOS outcome labels or new gold care plans
are invented. These dependent development variants are not an independent test
set or a clinical training cohort. They must receive independent source mapping
before being used for a new gold-based 100-case evaluation.

## Reproduction

From the repository root:

```powershell
python scripts/prepare_pilot.py
python scripts/score_pilot.py
python scripts/build_corrected_synthetic_benchmark.py
```

From `backend/`, using the configured local Groq key without printing it:

```powershell
python -m scripts.audit_probability
python -m scripts.pilot_judge --kind chunks --pause 65
python -m scripts.pilot_judge --kind plan --pause 65
```

Run `score_pilot.py` again to refresh the seven CSVs from completed checkpoints.
Do not run multiple judge workers concurrently against the same token budget.
The disposable CPU metrics image is built with `backend/Dockerfile.evaluation`;
the exact BERT/metric configuration and package versions are saved with results.

After all 80 plan stages are complete:

```powershell
python scripts/score_pilot.py
python scripts/analyze_pilot.py
python scripts/audit_pilot_source_ids.py
python scripts/plot_probability_audit.py
python scripts/build_pilot_report.py
python scripts/integrate_pilot_paper.py
python scripts/render_paper.py
python scripts/package_test_data.py
```

The final report and manuscript integration fail closed on incomplete plan
populations. `build_pilot_report.py --partial` explicitly produces an interim
report; no partial-arm quality mean is substituted for the full paired analysis.
`analysis.json` records descriptive paired case-bootstrap intervals, arm-rank
agreement, four-arm safety rates and suspect evaluator findings. Case resampling
does not remove source/template dependence.
