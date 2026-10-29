# 100-case care-plan research rerun

The same previously exposed synthetic benchmark is reused. This is a generation/audit rerun, not an independent clinical validation, retrieval re-benchmark, or paired verified/unverified ablation. The three-case gate passed before scaling. Unsupported sections remain explicit. No autonomous treatment orders are authorized.

| Guideline | Saved / planned | Reference-complete / saved | Model-contract failures / saved | Clinician reviews |
| --- | --- | --- | --- | --- |
| NICE | 40/40 | 39/40 | 0/40 | 0 |
| AAP | 30/30 | 21/30 | 0/30 | 0 |
| WHO | 30/30 | 7/30 | 0/30 | 0 |

## Changes and safeguards

- Audit batches contain at most four claims; every batch must pass schema/ID validation. An invalid batch approves no claims. Two distinct backbones remain required.
- Whole source paragraphs, including conditions and exceptions, are immutable; retained quotations were programmatically checked against retrieved passage text.
- Fixed-query BM25Plus source proposals and source-scoped supplements address missing topic coverage without gold/reference input. The context budget is larger than earlier retrieval experiments; this is not an isolated component ablation.
- Patient criteria and missing values are rendered separately. Numeric drug-dose rejection cannot be cleared by historical or conditional labelling.
- Fresh calls are checkpointed. Exact-prompt/model completed calls from the identical-pipeline pilot are reused and recorded; completed model/audit failures remain in quality counts. Provider failures are operational records, not fabricated clinical outputs.

## Interpretation

Reference completeness is an engineering coverage criterion, not safety, actionability or clinical usability. All 13 headings being present is insufficient. Cases and source/gold annotations remain unreviewed by a clinician. Previously reported Recall/MRR/Precision/nDCG retrieval results are unchanged and cannot be used as generation-quality scores. No new clinical accuracy or care-outcome metric is claimed.

The delivery CSV contains full original case JSON and history, engineering gold IDs and full passages with hashes, every generated section, patient met/not-met/unknown criteria, actual retrieved passages, release/error status and source-run hashes. Pending rows, if any, are explicitly labelled and contain no invented care plan.

Regression validation: 49 combined pipeline checks passed, followed by two checks of the concurrent key-pool transport. No live API response is treated as clinician sign-off.

## Completion and application integration

All 100 cases are saved: NICE 39/40, AAP 21/30 and WHO 7/30 pass reference completeness. Thirty-three outputs remain incomplete. These are not clinical success rates. The original 52 case records remain byte-identical. The fresh v23 candidate pilot was attempted after completion, but named-account quota exhaustion prevented a completed case; no v23 model score is claimed. The app uses its existing source selector with a new bounded audit adapter, strict input bounds, patient criteria/current measurements, uncertainty, caregiver communication and step-number formatting. The separate v23 topic-proposal algorithm is not promoted into the app. Validation: 68 backend tests and six Flutter tests passed; static analysis had no application errors (one demo-only informational import).
