# Development gate before a final research evaluation

The final evaluation is on hold at the user's request. Existing 100-case studies
and small answer pilots are development evidence, not a final or untouched test.
Earlier failures, source exclusions and API-blocked stages remain recorded.

The next candidate must first demonstrate all of the following on development
checks, with its model revisions, prompts, corpus and settings pinned:

- Recall@4 and MRR@4 targeted at 0.80 or higher **for each guideline separately**.
  Conventional Precision@4, nDCG@4, case and scenario-family intervals accompany
  these scores. Precision is not rescaled to conceal its annotation ceiling.
- No known wrong-onset, wrong-gestation or wrong-setting passage reaches a
  patient recommendation. Unknown eligibility stays explicit; missing is not normal.
- At least 90% structurally valid answers and 80% usable, fully reviewed answer
  coverage in a balanced development pilot covering all six families and three
  sources. Complete and partial releases are distinct; empty or irrelevant
  excerpts do not count as useful coverage. Provider failures have separate counts.
- Complete, noncontradictory audits of every emitted claim. No unsafe releases
  in the 36-fault regression suite, and no weakening of dose, quotation or
  stopping-condition checks to raise coverage.
- Remaining failures have case-level explanations and a review queue. Gold-ID
  uncertainty is audited separately; benchmark labels are never changed merely
  to improve a score.
- Relevant backend and app-contract regressions pass. Index migrations, encoder
  identity, scope review and source versions have a documented deployment path.

These are engineering entry criteria for a final research evaluation, not proof
of clinical effectiveness or authorization to treat patients. Clinical readiness
still requires source/gold adjudication and external clinical validation. The
current 100 cases have already been examined and cannot become an untouched test
by renaming a split. Any final report must disclose that exposure and the repeated
templates, retain negative results and avoid claims of superiority when paired
intervals include zero.

Current status: **not passed**. The completed consensus development regression
has Recall@4 of 0.6792, 0.7500 and 0.8000 for NICE, AAP and WHO; MRR@4 is
0.7875, 0.7083 and 0.8500, respectively. Recall@8 is 0.8333, 0.8333 and 1.0000,
but a larger context budget does not satisfy the unchanged four-passage gate.
The source-specific CSVs include both bootstrap interval types and negative
results. No balanced clinical answer usability pilot is established by these
retrieval scores. The listwise-only variant reduced WHO recall and is not adopted
as an availability gate. These are development results on exposed cases.
No final run or clinical deployment is approved by this document, and no
clinician sign-off is fabricated.
