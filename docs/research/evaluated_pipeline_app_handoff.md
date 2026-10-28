# Evaluated pipeline to application handoff

Requested order: improve the development candidate, pass the entry gate, freeze
and complete the final research evaluation, integrate that exact evaluated
pipeline into the application, then push the application and research to
`hadia-glitch/eosRAG`. The final integration and push have not occurred.

The prior public development commit is
`32ac217449b3039117ef8af2d69cf2b09a7c1017`. It does not establish that the
latest research candidate is deployed in the application.

## Before the final evaluation

- Retain the original 100 cases, source-specific gold identifiers, unsuccessful
  variants, provider transport records and development provenance. Reuse of
  exposed cases must be disclosed; it is not an untouched external validation.
- Apply the existing readiness gate without changing its targets after seeing
  results. Complete balanced answer checks and genuine semantic fault checks;
  a schema rejection before auditing is a structural check only.
- Freeze the selected models, revisions, prompts, index, graph, settings,
  evidence budget and hashes before the final experiment. Record the evaluated
  pipeline version explicitly in its result manifest.

## After the final evaluation

- Connect the evaluated retrieval and verification implementation to evidence
  search, care plans and case explanations. Keep request de-identification,
  history validation, cloud consent, source admission and scope checks before
  patient-conditioned retrieval.
- Preserve complete recommendations and their conditions when indexing. Verify
  corpus and encoder identities against the evaluated artifacts; changing the
  chunker, candidate pool or ranking algorithm creates a different pipeline.
- Capture and persist the inputs required by the selected pathway, including
  separate culture-incubation and antibiotic-exposure times. Unknown inputs
  must remain unknown. Distinguish respiratory support modalities and the
  source-specific observation fields supported by the workflow.
- Show patient-specific findings, missing information, longitudinal changes,
  recommendations, citations and verification status legibly in all three
  screens. An abstention must explain the actual missing prerequisite.
- Exercise complete requests through the app and API with the same synthetic
  cases used for integration regression. Confirm that evidence identifiers,
  context, safety outcomes and model versions match the evaluated service.
- Keep the risk predictor identified as a research model. Synthetic retrieval
  scores cannot establish calibrated EOS probabilities or clinical validation.
- Publish application code, reproducible research and updated manuscript to
  eosRAG using the publication checkout. Exclude keys, private data, caches,
  recordings, demo helpers and task scratch files. Review the actual staged
  diff and secret scan before pushing, then verify the remote commit.

Guideline approval and clinician review remain separate requirements. A passing
engineering evaluation does not grant approval for autonomous clinical use.
# Latest research input alignment (28 October 2026)

The improved RAG selector remains a development candidate and has not been
integrated into the active application or pushed. Its latest mean retrieval
targets pass on the exposed 100 cases, but generation and semantic safety gates
remain unmet. The new `LongitudinalInputsScreen`, accessible through the timeline
icon on Home, is a separate research input/observed-trend preview. It uses
authenticated `/api/v1/research/longitudinal/contract` and `/preview` endpoints,
enforces exact field alignment, preserves unknown maternal values, and requires
measurement and availability ages. It does not return a PIC risk score.

Actual-data PIC model development retains only seven independent positive
infants and has inadequate discrimination. No PIC model replaces the installed
research classifier, no synthetic obstetric record is joined to a real infant,
and no new probability is represented as clinical EOS risk. The model card,
aggregate comparisons and linked-cohort templates document the data needed.
Patient-level cohorts, partitions, predictions and real-data model weights stay
under ignored `data/picdb_private/`. The following historical handoff notes remain
context, not evidence that the new candidate has completed final evaluation.



## 28 October robustness audit

- NICE plain-wording fixed-plan Recall@4 remains 0.7667 after intent normalization (below 0.8 development target).
- AAP model-approved action prose omits a site-specific-infection exception; agreement does not establish semantic completeness.
- NICE draft mistakes unclear suspicion for reassuring eligibility and adds unsupported escalation; only a different structural issue blocks release.
- WHO model auditors disagree on illness-category conflation.
- Balanced usable-answer coverage and fresh semantic fault suite remain incomplete.
- Clinical source approval, gold adjudication, paraphrase equivalence and independent challenge cases remain unavailable.

Full numerical results and confidence intervals: output/research/rag_development/robustness_audit/all_retrieval_metrics.csv. No unchanged original-query score is evidence of independent generalisation.
