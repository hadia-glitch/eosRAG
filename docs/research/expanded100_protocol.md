# Three-guideline synthetic EOS evaluation

The active fixture is `output/research/expanded100/cases.json`: exactly 100
synthetic vignettes, consisting of 40 NICE, 30 AAP and 30 WHO cases. The original
18 cases are retained unchanged; the remaining 82 are additions. The six scenario
families have 17, 17, 17, 17, 16 and 16 cases. No patient-table rows are used.

The source indexes contain 132 NICE passages, 43 AAP passages and 141 WHO
passages. AAP cases use the 2018 report for infants born at least 35 weeks.
WHO cases use only the first-72-hour subset of its broader 0-59-day guidance.
Hospital versus non-hospital context and referral feasibility remain material.
Source identity was technically checked; clinical source approval, case
plausibility and gold relevance remain for clinician adjudication.

## Fixed definitions

- Case generation and bootstrap seed: 31. Bootstrap resamples: 2,000.
- Retrieval: unchanged BM25, MiniLM-L6-v2 exact dense cosine, hybrid and
  hybrid-plus-concepts implementations. Top-k is 4 and RRF offset is 60.
- Retrieval is source-gated; passage-level age/gestation/setting filters are not
  applied by the frozen ablation. The indexed scope annotations are review data.
- Primary generation and both auditors: `openai/gpt-oss-120b`, temperature zero,
  JSON-object response mode, no repair. The API sampling seed is unset and model
  aliases are not immutable provider snapshots.
- Both primary arms share the same initial draft. One arm emits it; the other
  releases the identical draft or withholds it. Released-only alignment is
  conditional and is reported beside release/quality-population counts.
- Secondary backbones: `openai/gpt-oss-20b` and `qwen/qwen3.8-27b`, each using the
  same 100 cases in paired zero- versus at-most-one-repair conditions. The
  historical 20-second minimum cloud-call gap and 120-second preflight budget
  are retained. Initial recorded elapsed time is deducted on replay. This is
  an admission check, not a hard wall-clock deadline during provider waits.
- The fault challenge is separate from the 100 patient vignettes: 36 deliberately
  corrupted drafts, 12 per guideline. Structural rejection, completed semantic
  rejection and invalid-verdict withholding are counted separately.
- BLEU uses corpus aggregation rather than a mean of sentence BLEU. METEOR,
  ROUGE and the fixed DistilBERT/RoBERTa BERTScore settings match the retained
  scoring implementation. Case and whole-scenario-family bootstrap intervals
  are descriptive; six related families do not establish population inference.

## Execution and checkpoints

From the repository root, using the installed backend runtime for API stages:

```powershell
python -X utf8 -m backend.scripts.evaluate_expanded primary
python -X utf8 -m backend.scripts.evaluate_expanded faults
python -X utf8 -m backend.scripts.evaluate_expanded judges
python -X utf8 -m backend.scripts.evaluate_expanded backbones
```

The isolated CPU metric runtime is used for retrieval/scoring:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m backend.scripts.evaluate_expanded retrieval
.\.venv\Scripts\python.exe -X utf8 -m backend.scripts.summarize_expanded --score-alignment
.\.venv\Scripts\python.exe -X utf8 -m backend.scripts.summarize_expanded
```

The last command refreshes saved judgments, tables and stage-completion counts
without regenerating candidates or recomputing BERTScore. Environment versions
are recorded in the generation/evaluation environment JSON files.

Each completed role is checkpointed by role, prompt hash and occurrence. The
occurrence distinguishes a fresh post-revision audit from the original audit.
Transport retries reuse completed responses, including unfavorable and malformed
ones. Provider errors remain in operational logs and outside quality scores.
Completed non-object JSON, malformed verdicts and truncated replies remain model
contract failures. No semantic failure is retried to obtain a better answer.
This includes provider decoder rejections of completed JSON generation, even
when the provider carries that contract failure in an HTTP 400 envelope.

## Historical comparison limits

The original 18 retrieval rankings replay exactly. Historical verifier code,
however, differs from the current frozen verifier. The retained old runner also
used transport defaults rather than forwarding completion options. Current
auditor limits are explicit at 1,000 tokens; exact historical verifier/transport
equivalence is not asserted. Original-18 controls and old-value comparison tables
support inspection without presenting this as a controlled runtime improvement.

The earlier 114-case retrieval-only prototype is superseded. The user-requested
100-case allocation used predetermined family quotas and case order. A logged
exact-text WHO deduplication corrected repeated PDF blocks; no retrieval
hyperparameter was tuned. Metadata-only corrections and quality-classification
corrections are retained as amendment records. A deterministic reconstruction
check reproduces the final case and corpus files byte for byte.

## Papers and clinician review

`scripts/update_expanded_paper.py` refuses a final manuscript update until primary
metrics, all fault tests, all judge stages and every declared backbone pair are
complete. `--preview` writes an explicitly incomplete layout preview under `tmp/`
and leaves the manuscript unchanged. Changed sentences, table lines and their
old/new number literals are listed in the final revision log.

`scripts/build_expanded_clinician_bundle.py` creates an offline case viewer,
source excerpts, blank rating CSV, source/case hashes and a review handbook.
Existing clinician annotations are preserved by case ID. The packet is not a
clinical sign-off; any adjudicated case/reference changes require a new version.
The earlier ten-case Phase 1 pilot is a separate historical experiment and its
results must not be pooled with this fixture.
