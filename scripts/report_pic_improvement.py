"""Aggregate nested results and single-event influence; no patient rows exported."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from ml.train_pic_longitudinal import weighting,metrics,write_csv
from ml.pic_dataset import save


def main():
    out=ROOT/'output/research/pic_longitudinal/nested_improvement'
    result=json.loads((out/'results.json').read_text());private=ROOT/'data/picdb_private'
    rows=[json.loads(s) for s in (private/'landmarks.jsonl').read_text().splitlines()]
    pred=json.loads((private/'nested_improvement/seed31.json').read_text())['predictions']
    groups=np.array([r['patient_id'] for r in rows]);y=np.array([r['label'] for r in rows]);w=weighting(rows)
    positive=sorted(set(groups[y==1]));influence=[]
    for method in ['nested_selected','compact_lr_knn_C01']:
        values=[]
        for omitted in positive:
            mask=groups!=omitted;values.append(metrics(y[mask],np.array(pred[method])[mask],w[mask]))
        influence.append({'method':method,'seed':31,'positive_infant_omissions':len(positive),
            'min_auprc_after_omission':min(v['auprc'] for v in values),'max_auprc_after_omission':max(v['auprc'] for v in values),
            'min_auroc_after_omission':min(v['auroc'] for v in values),'max_auroc_after_omission':max(v['auroc'] for v in values),
            'interpretation':'Sensitivity of fixed OOF predictions; not retrained leave-one-out validation.'})
    save(out/'positive_event_influence.json',influence);write_csv(out/'positive_event_influence.csv',influence)
    lines=['# PIC nested improvement experiment','',
        'Eight fixed model/imputation candidates were compared on the unchanged real PIC v1.1.0 cohort: 543 infants, seven positive infants, 1,436 pre-culture landmarks. No Kaggle or synthetic rows were added. Maternal data remain unavailable.',
        '', 'Three outer patient-disjoint folds and two inner folds select by inner patient-weighted AUPRC. Seeds 31, 47 and 83 are all retained. All preprocessing and nearest-neighbour donors are fitted using training-fold data only. The cohort was previously exposed in development; these are not independent final-validation results.',
        '', '## Results','', '| Method | Seed | AUROC | AUPRC | Brier |','|---|---:|---:|---:|---:|']
    for r in result['metrics']:
        lines.append(f'|{r["method"]}|{r["seed"]}|{r["auroc"]:.6f}|{r["auprc"]:.6f}|{r["brier"]:.6f}|')
    lines+=['','## Interpretation','',
        'The nested-selected procedure has AUROC 0.4280, 0.4059 and 0.6399 across seeds. Seed-31 AUROC has infant-bootstrap 95% interval [0.1371, 0.7038]; its AUPRC interval is [0.0047, 0.0600]. These results do not establish useful clinical discrimination or a reliable gain over the earlier forest. Selecting the largest outer AUROC or best seed would exaggerate evidence.',
        '', 'The KNN candidate has AUPRC 0.0935 at seed 31, but 0.0091 and 0.0080 at seeds 47 and 83. That isolated gain is not reproducible. Positive-infant omission diagnostics below use fixed predictions and cannot be interpreted as a retrained validation study.','']
    for r in influence:
        lines.append(f'- {r["method"]}: AUPRC after omitting one of seven positive infants ranges from {r["min_auprc_after_omission"]:.6f} to {r["max_auprc_after_omission"]:.6f}.')
    lines+=['', '## Data and availability audit','',
        'The supplied archive is v1.1.0; the pasted PhysioNet page describes v1.0.0. Source: https://physionet.org/content/picdb/1.1.0/. This is real hospital EHR data, but the present endpoint is an unadjudicated early blood-culture pathogen phenotype, not an independently adjudicated clinical EOS outcome.',
        '', 'LABEVENTS contains CHARTTIME but no verified result-availability timestamp. Laboratory results are therefore not imported into pre-culture prediction as if already available. EMR_SYMPTOMS includes RECORDTIME, but NLP symptom attribution and originating document type need review before using it for clinical forecasting. Discharge diagnoses, culture results, medications and patient identifiers remain excluded as predictors.',
        '', 'The existing seven-positive-infant cohort cannot establish calibration, treatment thresholds or broad clinical reliability. A larger linked maternal-neonatal cohort with result/document availability and EOS outcome adjudication remains the main requirement. More landmarks or synthetic oversampling do not create independent infection outcomes.',
        '', '## Status','',
        'No new candidate is promoted to the app, and the current Kaggle research predictor is unchanged. The final RAG evaluation and publication push remain on hold. No Groq calls or external patient-data transfers were used. Nine relevant regression tests passed (one unchanged authenticated API test excluded from this run). Restricted patient-level predictions stay under ignored data/picdb_private; public files contain aggregate results only.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    card=ROOT/'docs/research/pic_longitudinal_model_card.md';marker='\n\n## Nested imputation and model-selection experiment'
    text=card.read_text().split(marker)[0]+marker+'\n\nEight candidates including distance-weighted five-neighbour imputation, compact temporal features, regularized logistic regression, forests, Extra Trees and native-missingness boosting were tested with three outer/two inner patient-separated folds at three seeds. Nested-selected AUROC was 0.4280, 0.4059 and 0.6399; primary-seed 95% CI [0.1371, 0.7038]. The KNN AUPRC gain was unstable across seeds. No candidate is promoted. Full results: output/research/pic_longitudinal/nested_improvement/report.md.\n'
    card.write_text(text,encoding='utf8')
    print(json.dumps({'report':str(out/'report.md'),'influence':influence,'clinical_ready':False}))


if __name__=='__main__':main()
