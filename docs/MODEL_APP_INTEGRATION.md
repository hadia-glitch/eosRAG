# Connected trained model and input contract

The app's results tab now calls the installed **postnatal-days-0-2 calibrated
forest** through `/api/v1/research/model/predict`. This is the actual fitted
artifact, not a point-score substitute. It is bundled in
`backend/ml/deployed/supplied_neonatal/` with model/scope digests. The EOS clinical
model remains a separate gated contract: supplied observation labels have not
been established as culture-confirmed EOS outcomes.

Workflow: create/update assessment -> save -> results -> **Review model inputs &
predict** -> review all 18 fields, explicitly mark unknowns, confirm -> save and
run inference. The result displays supplied-label probability, imputation,
model version, research status and actual model input effects. The current input
effects initially shown are median-replacement differences, **not SHAP**. The
**Explain with SHAP** button requests actual local Kernel SHAP for the served
calibrated forest; additivity and prediction parity are checked before display.
The reference is the aggregate fit-median/modal vector, not a clinical norm.
No dose, antibiotic
decision or clinical risk category is derived from this research output.

The form is driven by the server's input contract. A client allowlist rejects
unknown fields and excludes names, MRNs, dates and notes. The server rejects
extra fields, text in numeric slots, booleans as measurements, non-finite values,
invalid categories, missing baseline values and inconsistent postnatal ages.
Out-of-development-support values cause abstention rather than clamping.
The client checks the server's development ranges before submission. At most
three measurements may be unknown (the fit-partition 99.5th percentile); the
form explains when too many values are missing, without suggesting guessed
measurements. A research result never replaces the unavailable clinical EOS
model with a low-risk label.

| Model input | App source / handling |
| --- | --- |
| Gestational_Age | Current assessment, weeks; reviewable |
| Birth_Weight | Measured birth weight; grams to kg is the only automatic quantity conversion |
| Sex | Required selection matching the recorded training categories; never inferred from a name |
| Postnatal_Age | Completed days, derived from assessment age in hours; read-only |
| Delivery_Mode | Assessment; Caesarean normalized to dataset spelling Cesarean |
| Apgar | Assessment score; integer validation |
| HR | Numeric measured beats/min in the review form; also forwarded to clinical history |
| Resp | Numeric measured breaths/min; also forwarded to clinical history |
| Temp | Assessment degrees C; explicit unknown suppresses the default from RAG context |
| SpO2 | Numeric measured percentage; also forwarded to clinical history |
| BP | Dataset mmHg value; source does not identify pressure type |
| Oxygen | Numeric research value, kept separate from categorical oxygen support |
| WBC / CRP / PCT / Platelets / Lactate / Hemoglobin | Raw research inputs with undocumented dataset units. Clinical values are not silently rescaled or copied. Leave unknown unless mapping is documented. |

Birth weight, care setting and research measurements now survive local/remote
patient-record serialization and follow-up edits. The misleading entry footer
showing zero points/Low Risk has been replaced with a measurement-entry status.
The evidence screen also no longer displays or forwards that retired score.
Review and assessment timestamps are retained. A later assessment cannot
re-date the previous HR/respiratory-rate/SpO2 as freshly recorded observations;
those fields enter the clinical snapshot only when reviewed for that assessment.
Previously entered values are visibly identified as requiring review.
Historical rule-score code is not used by this connected model endpoint.

For local use, run the authenticated backend from `backend/` with
`python -m uvicorn main:app --host 127.0.0.1 --port 8000`, then build the client
with `scripts/build_local_web.ps1` (reads only public values from the root .env).
For Vercel, use the HTTPS API host in the deployment runbook. Model availability
does not establish hosted Supabase/auth availability: local zero-row probes still
returned connection errors and no live database migration is claimed.

Research inference reports audit availability and remains research-only when the
audit database is unreachable. Set RESEARCH_PREDICTION_REQUIRES_AUDIT=true to
require a recorded audit even for research estimates. Clinical prediction and
care-plan endpoints retain their mandatory audit release condition.

Small nonzero probabilities display as `<0.1%` rather than rounding to zero.
The display remains a supplied-label probability, not an EOS treatment threshold.

Clinical evidence requests now accept only the typed de-identified patient
snapshot. Clients cannot inject their own previous-assessment history; the
server loads history after encounter ownership checks. The plan response has
thirteen review sections, explicit undetermined/withheld states, source links
and a visible audit/revision trail. Strict provider response schemas constrain
quote IDs to retrieved evidence and audit IDs to actual draft claims. One
bounded revision is permitted after completed dissent, followed by both audits.
