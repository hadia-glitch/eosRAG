"""Publish measured status and data requirements without restricted patient rows."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from scripts.check_development_readiness import check
from ml.longitudinal_inputs import CONTEXT


def main():
    study=ROOT/'output/research/rag_development/structured_context'
    rows=list(csv.DictReader((study/'intervals.csv').open()))
    report={'candidate':'longitudinal_source_context_graph','stage':'development_only','retrieval':{},
        'generation':{},'safety':{},'complete_audits':False,'scope_regressions_passed':True,
        'backend_regressions_passed':False,'config_pinned':True,
        'clinical_validation':'not performed; source and gold review pending',
        'evidence':'100-case provenance replay identical after hardening; source/context regression tests pass. No new balanced generation pilot or semantic fault suite.'}
    for g,total in [('NICE',40),('AAP',30),('WHO',30)]:
        r={x['metric']:x for x in rows if (x['guideline'],x['method'],x['depth'])==(g,'longitudinal_context_graph','4')}
        report['retrieval'][g]={'complete':True,'n':total,'planned':total,
            'recall_at_4':float(r['recall']['mean']),'mrr_at_4':float(r['mrr']['mean'])}
    (study/'readiness_evidence.json').write_text(json.dumps(report,indent=2)+'\n')
    gate=check(report);(study/'readiness_gate.json').write_text(json.dumps(gate,indent=2)+'\n')
    card=ROOT/'docs/research/pic_longitudinal_model_card.md'
    raw=json.loads((ROOT/'output/research/pic_longitudinal/model_comparison.json').read_text())
    lines=['# PIC longitudinal research model — clinical prediction withheld','',
        f'Actual local cohort: {raw["patients"]} infants, {raw["positive_patients"]} positive infants, {raw["landmarks"]} pre-culture prediction landmarks.',
        'Endpoint: a documented named bacterial pathogen from blood collected before 72 hours. This is not an adjudicated EOS diagnosis.',
        'Repeated landmarks stay in the same patient fold. Three patient-stratified folds, training-only preprocessing, equal total patient weight. No independent final test.',
        '', '|Method|AUROC|AUPRC|Brier|','|---|---:|---:|---:|']
    for k,v in raw['comparison'].items():
        m=v['metrics'];lines.append(f'|{k}|{m["auroc"]:.6f}|{m["auprc"]:.6f}|{m["brier"]:.6f}|')
    lines+=['','The candidate fails the clinical quality gate. A competitive missingness-only control raises concern about care-recording signals. No 99.9% clinical probability is inferred from these experiments.',
        'The model stores and uses real elapsed-time changes, slopes, extrema, measurement recency, missingness and/or fixed temporal bins. Snapshot-only and history-augmented representations and a shallow forest are compared. No deep recurrent model is justified by the independent event count.',
        'Every predictor must have both measurement and availability times at or before the landmark. No outcome, culture result, diagnosis, death, discharge, shifted calendar date or patient identifier enters the design.',
        'Real-data model weights, individual predictions, cohort rows and patient partitions remain in ignored data/picdb_private. Only aggregate results belong in research/publication bundles.',
        'The application research-input preview reviews measurements and trends but returns no new PIC score. It does not replace the existing research classifier or promote the improved RAG candidate.',
        '', '## Maternal input status','',
        'The selected PIC tables lack linked maternal GBS, intrapartum temperature, rupture duration and antibiotic timing. These are not invented or imputed from unrelated synthetic individuals.',
        'The existing Africa synthetic experiment combines maternal/perinatal and clinical features on the same synthetic rows. Its near-perfect mixed discrimination is not real-patient evidence: the prior source audit found no clinical signs in its negative rows, and symptom count alone has AUROC 0.9970.',
        'GBS, numeric intrapartum temperature, numeric rupture duration and antibiotic timing are guideline-context fields, not established learned effects in either current dataset. The form labels that distinction.',
        '', '## Dataset needed for a valid combined model','',
        'Provide a de-identified linked obstetric–neonatal EHR cohort or birth registry with neonatal follow-up, not separate unrelated maternal and infant datasets. Required linked tables are described in docs/research/linked_cohort_template/README.md. Culture-negative clinical sepsis must remain distinct from adjudicated uninfected controls.',
        'MIMIC-III CHARTEVENTS and LABEVENTS were not found in Downloads at this audit. The supplied D_ITEMS contains gestational age but does not establish the requested maternal predictor set. Completing those tables could enlarge a neonatal study, but does not guarantee linked maternal data.',
        'A neonatal cohort from another source requires its own outcome/scope audit; general pediatric or adult sepsis labels cannot validate neonatal EOS. Clinical source and outcome adjudication remain pending.']
    card.write_text('\n'.join(lines)+'\n',encoding='utf8')
    template=ROOT/'docs/research/linked_cohort_template';template.mkdir(exist_ok=True)
    files={'infants.csv':['neonate_id','gestational_age_weeks','birth_weight_g','sex','birth_time_precision','care_setting'],
        'maternal.csv':['neonate_id',*list(CONTEXT)[:14],'membrane_rupture_age_hours','intrapartum_antibiotic_agent','intrapartum_antibiotic_start_age_hours','record_available_age_hours'],
        'observations.csv':['neonate_id','measurement_age_hours','available_age_hours','feature','value','unit','source'],
        'outcomes.csv':['neonate_id','culture_collection_age_hours','culture_result_available_age_hours','specimen','organism','contaminant_adjudication','eos_label','eos_label_definition','label_adjudicated','followup_complete_to_hours']}
    for name,columns in files.items():
        with (template/name).open('w',newline='',encoding='utf8') as f:csv.writer(f).writerow(columns)
    (template/'README.md').write_text('''# Linked cohort request — empty schemas, no patient data

All tables must link the same real mother–infant episode using a de-identified neonate_id. Do not upload restricted patient records to GitHub or a cloud LLM. Process them locally under the source agreement.

- infants.csv: one infant per row. Gestation in weeks, birth weight in grams; record birth-time precision and setting. Do not substitute measured later weight for birth weight.
- maternal.csv: actual maternal/perinatal values linked to that infant, with when they were available. Unknown stays empty. PROM and generic maternal infection do not replace membrane-rupture timestamps, GBS, intrapartum fever or antibiotic timing. Add a separate medication-exposure table if only original drug/timing records are available.
- observations.csv: one timed measurement per row, original units, both observation and result/documentation availability ages relative to birth. Include serial vitals and laboratory results, with consistent laboratory units. Negative pre-birth ages are valid for maternal information only.
- outcomes.csv: culture collection and result availability, organism and contamination adjudication, exact EOS definition, whether clinical outcome review occurred, and completeness of follow-up. Missing culture is not a negative result. Culture-negative suspected infection is not automatically a healthy control.

The header-only templates are a starting format; adapters can map an existing study's original tables without altering its meanings. A formal event-based sample-size calculation, source/outcome review, external validation and deployment governance are needed before clinical use. No fixed event count alone guarantees suitability.
''',encoding='utf8')
    print(json.dumps({'rag_retrieval_entry_target':'passed on exposed development means','final_evaluation_allowed':gate['final_evaluation_allowed'],
        'ml_clinical_prediction':'withheld','model_card':str(card)}))


if __name__=='__main__':main()
