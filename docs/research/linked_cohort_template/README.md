# Linked cohort request — empty schemas, no patient data

All tables must link the same real mother–infant episode using a de-identified neonate_id. Do not upload restricted patient records to GitHub or a cloud LLM. Process them locally under the source agreement.

- infants.csv: one infant per row. Gestation in weeks, birth weight in grams; record birth-time precision and setting. Do not substitute measured later weight for birth weight.
- maternal.csv: actual maternal/perinatal values linked to that infant, with when they were available. Unknown stays empty. PROM and generic maternal infection do not replace membrane-rupture timestamps, GBS, intrapartum fever or antibiotic timing. Add a separate medication-exposure table if only original drug/timing records are available.
- observations.csv: one timed measurement per row, original units, both observation and result/documentation availability ages relative to birth. Include serial vitals and laboratory results, with consistent laboratory units. Negative pre-birth ages are valid for maternal information only.
- outcomes.csv: culture collection and result availability, organism and contamination adjudication, exact EOS definition, whether clinical outcome review occurred, and completeness of follow-up. Missing culture is not a negative result. Culture-negative suspected infection is not automatically a healthy control.

The header-only templates are a starting format; adapters can map an existing study's original tables without altering its meanings. A formal event-based sample-size calculation, source/outcome review, external validation and deployment governance are needed before clinical use. No fixed event count alone guarantees suitability.
