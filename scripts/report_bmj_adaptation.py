"""Public aggregate report of the requested paper-inspired comparison."""
import csv,hashlib,json,zipfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/research/bmj_boruta_adaptation'


def main():
    r=json.loads((OUT/'results.json').read_text());p=r['protocol']
    assert hashlib.sha256((ROOT/'backend/ml/evaluate_bmj_adaptation.py').read_bytes()).hexdigest()==p['code_sha256']
    assert all(s['patient_overlap']==0 for s in r['splits'])
    for filename,rows in [('metrics.csv',r['metrics']),('intervals.csv',r['intervals']),('paired_auroc.csv',r['paired']),('splits.csv',r['splits'])]:
        with (OUT/filename).open('w',newline='',encoding='utf8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    feature_rows=[{'dataset':s['dataset'],'fold':s['fold'],'confirmed':len(s['confirmed']),'retained':len(s['selected']),
        'selected_features':'|'.join(s['selected_names']),'independent_selection_infants':s['selector_infants'],
        'positive_selection_infants':s['positive_selector_infants'],'status':s['selector_status']} for s in r['features']]
    with (OUT/'selected_features.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=list(feature_rows[0]));writer.writeheader();writer.writerows(feature_rows)
    lines=['# BMJ EOS paper-inspired Boruta / Random Forest experiment','',
        'Requested paper: Kainth et al., BMJ Paediatrics Open 2026;10:e003561, https://doi.org/10.1136/bmjpo-2025-003561. The public repository contains training R code, not a supplied fitted model or study dataset. No attached R code is executed.','',
        '## What is tested','',
        'This is an adaptation using the available Kaggle/PIC features, not reproduction of the published model or external validation of its weights. The paper uses 28 maternal/neonatal/clinical/care variables and 548 culture-positive development cases, while this PIC forecasting cohort has seven positive infants. The source R code and paper prose differ in selection computation: prose specifies 1,000 Boruta trees, while repository calls specify 10,000 trees/maxRuns 2,000. This experiment pins BorutaPy 0.4.3, 1,000 shallow trees and a 30-iteration cap. Python Gini importance differs from the R selector. All departures remain explicit.','',
        'Three arms compare an all-feature forest, a class-balanced forest, and Boruta plus correlation pruning plus the same class-balanced forest. The final forest uses 120 trees, max depth 8 and up to five candidate variables per split, following the public RF settings where possible. The feature selector uses one latest training observation per infant so repeated landmarks are not counted as independent significance evidence. The Kaggle record order does not establish true clinical chronology. Confirmed features only are retained; tentative features are not silently accepted. Absolute training Pearson correlation >0.7 drops the lower-training-importance feature.','',
        'Training-only infant-normalized class weights replace ROSE oversampling. This preserves observed labels where Kaggle outcomes vary within a patient ID and does not invent a single outcome for that infant. No synthetic patient, maternal history or clinical value is generated. If no feature is confirmed, a declared training-prevalence statistical fallback is retained rather than silently using rejected features. Such a fallback is not a clinically released predictor.','',
        'Kaggle uses the original patient-ID-disjoint partitions: fit 55%, independent threshold selection 15%, test 15%; the original separate calibration 15% is unused. PIC retains the original seed-31 three outer patient folds. Each outer training population reserves 25% per class (at least one positive infant) for threshold selection. Feature selection and forest fitting use only the remaining fit infants. PIC predictions precede first early blood culture and use only measurement/availability times already known at the landmark. Maternal, late laboratory, centre-prevalence and lagged device-exposure fields missing from the local data are not fabricated.','',
        'Thresholds maximize specificity while attaining >=90% sensitivity on the threshold set only. This is a target, not a guaranteed held-out sensitivity. Zero is allowed, exposing an all-positive degenerate solution if necessary. Forest seeds 31/47/83 share fixed patient partitions and a fixed training feature selector; these assess forest-randomization stability, not independent new cohorts or repeated feature-selection seeds.','',
        '## Primary forest-seed results','',
        'Every metric gives each infant equal total weight across its observations. Kaggle has 1,598 test rows from 509 held-out IDs; PIC has 1,436 out-of-fold landmarks from 543 infants. Old row-unweighted Kaggle metrics must not be compared directly as if the weighting were identical.','',
        '| Dataset | Arm | AUROC | Accuracy | Sensitivity | Specificity | Precision |','|---|---|---:|---:|---:|---:|---:|']
    for v in r['metrics']:
        if v['seed']==31:
            lines.append('|'+v['dataset']+'|'+v['arm']+'|'+f'{v["auroc"]:.4f}'+'|'+'|'.join('undefined' if v[k] is None else f'{100*v[k]:.2f}%' for k in ['accuracy','sensitivity','specificity','precision'])+'|')
    lines+=['','The adaptation does not establish better reliability. PIC Boruta AUROC is lower than both comparison forests, and the 90% held-out sensitivity target is missed. On Kaggle, Boruta discrimination is slightly lower than the balanced all-feature forest despite similarly high label-reproduction scores. Its three forest seeds remain below 90% held-out sensitivity; test thresholds are not retuned after seeing this failure.','',
        '## Paired discrimination and uncertainty','']
    for v in r['paired']:lines.append(f'- {v["dataset"]}: Boruta-balanced minus all-feature balanced forest AUROC interval [{v["low_95"]:.6f}, {v["high_95"]:.6f}].')
    lines+=['','All metric intervals use 2,000 infant-level resamples of fixed held-out predictions. They do not include all refitting, endpoint uncertainty or between-site transport. Full accuracy/sensitivity/specificity/precision/AUROC/AUPRC/Brier intervals and all three forest seeds are retained in CSV.','',
        '## Selected features and small-event limitation','']
    for v in feature_rows:lines.append(f'- {v["dataset"]} fold {v["fold"]}: {v["retained"]} retained features from {v["positive_selection_infants"]} positive selector infants: {v["selected_features"] or "none"}.')
    lines+=['', 'PIC selection of recency/count/age features raises recording-process confounding concerns. A threshold set containing only one positive infant can reach 100% sensitivity on that one infant and still generalize poorly. The simple all-positive PIC classifier would already have 100% sensitivity, 0% specificity, and precision/accuracy 7/543 (1.29%); sensitivity alone cannot establish reliability.','',
        'The paper reports roughly 90% internal sensitivity and 40.6% specificity, and external sensitivity 92.3% with specificity 37.2% on its own validation cohort. Those are not performance targets guaranteed for this different cohort or the adapted model. Its held-out external cohort is evidence unavailable in the present local experiments.','',
        'The Kaggle endpoint remains an unadjudicated supplied label with inconsistent patient/hour records, unstable immutable covariates and unverified timing/units. A high score does not repair that provenance. PIC has stronger source provenance, but its unadjudicated named-pathogen phenotype, seven independent events and missing maternal/clinical inputs prevent claiming a reliable clinical EOS predictor. Neither resampling nor a feature selector creates new independent positive outcomes.','',
        'No probability is independently calibrated for clinical EOS; class balancing can shift score priors. No treatment, stopping, discharge or deployment threshold is endorsed. All candidates remain local research outputs; app model, final RAG evaluation and GitHub publication remain unchanged. No Groq calls or external patient-data transfers are used.','',
        '## Reproduction','',
        'Install pinned Boruta 0.4.3 into tmp/bmj-model-deps (no dependency overwrite), then run python backend/ml/evaluate_bmj_adaptation.py with the existing source files and private PIC cohort. The script creates its private output folders. Protocol and private checkpoints are hash-pinned. Three regression tests check mixed-label weighting, sensitivity threshold selection and constant-score degeneration. No real patient rows, individual predictions or fitted joblib estimators are included in the public archive.','',
        'Public training code reference: https://github.com/tavlab-iiitd/EOS_Prediction_Modeling ; Python selector documentation: https://github.com/scikit-learn-contrib/boruta_py .']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    files=[v for v in OUT.iterdir() if v.is_file() and v.name!='manifest.json']
    files += [ROOT/'backend/ml/evaluate_bmj_adaptation.py',ROOT/'backend/tests/test_bmj_adaptation.py',ROOT/'scripts/report_bmj_adaptation.py']
    files += [ROOT/'docs/research/manuscript.md',ROOT/'output/pdf/neoguard-eos-research-paper.pdf']
    manifest={'stage':'development_only','clinical_ready':False,'raw_rows_or_model_weights_included':False,
        'files_sha256':{v.relative_to(ROOT).as_posix():hashlib.sha256(v.read_bytes()).hexdigest() for v in files}}
    m=OUT/'manifest.json';m.write_text(json.dumps(manifest,indent=2)+'\n');files.append(m)
    archive=OUT.parent/'neoguard-bmj-model-comparison.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for v in files:z.write(v,v.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in manifest['files_sha256'].items())
        assert not any(n.startswith('data/') or n.endswith('.joblib') or n.endswith('.env') for n in z.namelist())
    print(json.dumps({'report':str(OUT/'report.md'),'archive':str(archive),'clinical_ready':False}))


if __name__=='__main__':main()
