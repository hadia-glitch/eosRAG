"""Package aggregate diagnostic development results, never patient rows/weights."""
import csv,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/research/new_neonatal_cohorts'


def main():
    result=json.loads((OUT/'results.json').read_text());protocol=result['protocol']
    if hashlib.sha256((ROOT/'backend/ml/evaluate_new_cohorts.py').read_bytes()).hexdigest()!=protocol['code_sha256']:raise ValueError('Training code drift')
    for name in ['workbook','chop']:
        p=ROOT/f'data/new_neonatal_cohorts/{name}.json'
        if hashlib.sha256(p.read_bytes()).hexdigest()!=protocol['prepared_cohort_sha256'][name]:raise ValueError('Prepared cohort changed')
        for seed in protocol['seeds']:
            r=json.loads((p.parent/name/f'seed{seed}.json').read_text())
            if r['protocol_sha256']!=hashlib.sha256((OUT/'protocol.json').read_bytes()).hexdigest():raise ValueError('Checkpoint mismatch')
            if any(v['patient_overlap']!=0 for v in r['selections']):raise ValueError('Patient overlap')
    lines=['# New neonatal cohort model experiments','',
        'Separate exploratory diagnostic studies; not a pooled or validated EOS risk model. No app model is replaced. Original files remain unchanged. No Groq calls or external patient-data transfers were used.','',
        '## Cohorts','',
        '- Workbook: 138 preterm infants, 69 culture-positive cases and 69 controls. The codebook defines CASE=2 and CONTROL=1. Twelve features include maternal age, sex, gestation, delivery mode, birth weight, growth category and five blood-count measures. Identifiers and SEPSIS SIGNS (an exact copy of the outcome) are excluded. Six redundant derived indices and category duplicates are excluded. Weeks+days are parsed using days/7; counts are log-transformed where specified, without silently repairing source outliers.',
        '- CHOP: 580 evaluations in 472 infants aged <28 days; 53 bacteremic evaluations in 52 infants. Bacteremia is compared with sepsis-group-2 culture-negative rule-out episodes; other clinical/fungal/viral/indeterminate and non-blood-culture-positive groups are excluded. Fourteen baseline/evaluation-time features are used. IDs, culture results, treatment timing, mortality, length of stay, future support-free days and evaluation-day maximum temperature are excluded. Repeated episodes remain grouped by infant. This is not a clinical EOS cohort; the age-0–2-day subset contains only one bacteremic infant.',
        '- The supplementary ZIP contains two R scripts for the same CHOP study and no additional training records. No script from the attachment is executed.','',
        '## Validation','',
        'Five outer patient-separated folds with three inner folds. Candidate selection uses inner AUROC; decision thresholds maximize inner balanced accuracy on a fixed 0.05–0.95 grid. Outer outcomes do not select a model or threshold. Median imputation, indicators and scaling are fitted in training folds. Each infant has equal total loss/evaluation weight. Candidates are two regularized logistic regressions, Random Forest, Extra Trees and shallow gradient boosting. A demographic-only baseline is retained. Seeds 31/47/83 and all fixed-candidate results remain reported. This is internal development, not independent external validation.',
        '', '## Nested-selected results','',
        '| Dataset | Seed | AUROC | Accuracy | Sensitivity | Specificity | Precision | AUPRC |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in result['metrics']:
        if r['method']=='nested_selected':
            lines.append(f'|{r["dataset"]}|{r["seed"]}|{r["auroc"]:.4f}|{100*r["accuracy"]:.2f}%|{100*r["sensitivity"]:.2f}%|{100*r["specificity"]:.2f}%|{100*r["precision"]:.2f}%|{r["auprc"]:.4f}|')
    lines+=['','## Primary-seed 95% intervals','',
        '2,000 infant-level bootstrap resamples of fixed out-of-fold predictions. These intervals do not capture all model-refitting, phenotype or between-site uncertainty.','',
        '| Dataset | Metric | Lower | Upper |','|---|---|---:|---:|']
    for r in result['intervals']:
        if r['method']=='nested_selected':lines.append(f'|{r["dataset"]}|{r["metric"]}|{r["low_95"]:.4f}|{r["high_95"]:.4f}|')
    lines+=['','## Added signal versus demographics','']
    for r in result['paired']:
        lines.append(f'- {r["dataset"]}: paired AUROC difference {r["mean"]:+.4f}, 95% interval [{r["low_95"]:+.4f}, {r["high_95"]:+.4f}].')
    lines+=['','The workbook interval includes zero, and the baseline is higher at seeds 47 and 83. Thus an incremental blood-count benefit is not established consistently. CHOP has a positive primary-seed interval in this internal comparison, but low precision and specificity remain material limits. Its evaluation-time features may reflect an already unwell infant and are not pre-symptom forecasts.',
        '', '## Comparison and limitations','',
        'These AUROCs are more encouraging than the earlier PIC nested-selected values (0.4280/0.4059/0.6399), but the cohorts and outcomes differ. This is not a paired improvement of the PIC EOS model. The Kaggle near-perfect label-reproduction score is not a clinical performance target.',
        '', 'The workbook is a selected 50:50 preterm case-control sample: precision and absolute probability do not transfer to routine EOS prevalence. No individual postnatal/onset or result-availability times establish an EOS-only subgroup. CHOP is conditioned on sepsis evaluation and a treatment-duration-informed rule-out phenotype; controls are not adjudicated healthy infants. CHOP includes evaluation-time support features, no raw serial vital-sign/laboratory histories and no linked maternal GBS/fever/rupture/antibiotic history. Neither experiment validates longitudinal EOS prediction or treatment decisions. No clinical verification has been performed.',
        '', 'Source units and extreme workbook values require review before deployment. The source TOTAL COUNT value 163000 is retained, not silently changed to 16300. Log transformation limits leverage without claiming a correction. No observed result justifies excluding difficult rows or redefining outcomes to improve scores.',
        '', 'Five gestational-age parsing regression tests passed. Feature/source hashes, saved protocols, all 30 outer fold separations and private prediction checkpoints were verified. Model weights and individual predictions remain under ignored data/new_neonatal_cohorts. The public bundle includes only aggregate metrics, methods and code.',
        '', 'Sources: https://doi.org/10.6084/m9.figshare.28395161.v1 ; https://f1000research.com/articles/14-390/v4 ; https://data.mendeley.com/datasets/5vdz5cftz7/1 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC6881601/']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    files=[p for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json']
    files += [ROOT/'backend/ml/evaluate_new_cohorts.py',ROOT/'backend/tests/test_new_cohort_preparation.py',ROOT/'scripts/report_new_cohort_models.py']
    files += [ROOT/'docs/research/manuscript.md',ROOT/'output/pdf/neoguard-eos-research-paper.pdf']
    manifest={'clinical_ready':False,'app_model_changed':False,'patient_rows_included':False,'real_patient_weights_included':False,
        'files_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    save=OUT/'manifest.json';save.write_text(json.dumps(manifest,indent=2)+'\n');files.append(save)
    archive=OUT.parent/'neoguard-new-cohort-model-results.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in manifest['files_sha256'].items())
        assert not any(n.startswith('data/') or n.endswith('.joblib') or n.endswith('.env') for n in z.namelist())
    print(json.dumps({'report':str(OUT/'report.md'),'bundle':str(archive),'outer_folds_verified':30,'patient_data_exported':False}))


if __name__=='__main__':main()
