"""Audit and fit the supplied, unadjudicated neonatal CSV without promoting it to EOS.

Run from backend: python -m ml.research_cohort --archive PATH --output ../output/research
The exported JSON is deliberately incompatible with the clinical EOS contract.
Patient identifiers and source rows are never written to public reports.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

from ml.train import metrics, export_estimator

SEED = 31
CATEGORICAL = ['Sex', 'Delivery_Mode']
EXCLUDE = {'Patient_ID', 'Observation_Hour', 'Sepsis_Label'}


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf8')


def audit(d, raw_hash):
    g = d.groupby('Patient_ID')
    baseline = ['Gestational_Age', 'Birth_Weight', 'Sex', 'Delivery_Mode', 'Apgar']
    pairs = d.groupby(['Patient_ID', 'Observation_Hour'])
    return {'csv_sha256': raw_hash, 'rows': len(d), 'patient_ids': int(g.ngroups),
            'positive_rows': int(d.Sepsis_Label.sum()), 'prevalence': float(d.Sepsis_Label.mean()),
            'missing_by_column': {c: int(v) for c, v in d.isna().sum().items()},
            'duplicate_patient_hour_rows': int(d.duplicated(['Patient_ID', 'Observation_Hour']).sum()),
            'conflicting_label_patient_hour_pairs': int((pairs.Sepsis_Label.nunique() > 1).sum()),
            'inconsistent_baseline_patient_ids': {c: int((g[c].nunique() > 1).sum()) for c in baseline},
            'postnatal_age_days_range': [int(d.Postnatal_Age.min()), int(d.Postnatal_Age.max())],
            'birth_weight_at_upper_value_fraction': float((d.Birth_Weight == d.Birth_Weight.max()).mean()),
            'source': 'User-supplied Kaggle neonatal sepsis CSV; dataset URL, study, collection sites and label adjudication unavailable',
            'clinical_eos_eligible': False,
            'limitations': ['Sepsis_Label is an observation-associated supplied label, not established culture-confirmed EOS',
                           'Patient/hour conflicts and changing immutable covariates prevent defensible longitudinal reconstruction',
                           'Unit definitions and actual measurement/result availability times are unavailable',
                           'Real-patient versus generated-data provenance is unverified; distribution patterns do not prove either origin']}


def partitions(d):
    ids = np.array(sorted(d.Patient_ID.unique()))
    # Fixed patient-disjoint random partitions, never a temporal validation claim.
    fit, rest = train_test_split(ids, train_size=.55, random_state=SEED)
    cal, rest = train_test_split(rest, train_size=1/3, random_state=SEED + 1)
    val, test = train_test_split(rest, test_size=.5, random_state=SEED + 2)
    sets = [set(x) for x in (fit, cal, val, test)]
    assert all(not sets[i] & sets[j] for i in range(4) for j in range(i))
    return sets


def bootstrap(y, p, groups, threshold, repeats=300):
    rng = np.random.default_rng(SEED)
    unique = np.unique(groups)
    indices = [np.flatnonzero(groups == x) for x in unique]
    estimates = {k: [] for k in ['auroc', 'auprc', 'brier', 'sensitivity', 'specificity']}
    for _ in range(repeats):
        ix = np.concatenate([indices[i] for i in rng.integers(0, len(unique), len(unique))])
        if len(np.unique(y[ix])) != 2:
            continue
        m = metrics(y[ix], p[ix], threshold)
        for k in estimates:
            estimates[k].append(m[k])
    return {k: np.quantile(v, [.025, .975]).tolist() for k, v in estimates.items()}


def portable_probability(a, x):
    if a['kind'] == 'logistic':
        z = x @ np.array(a['coefficients']) + a['intercept']
        p = 1 / (1 + np.exp(-np.clip(z, -700, 700)))
    else:
        # sklearn tree inference casts predictors to float32 before branching.
        x = x.astype(np.float32)
        outputs = []
        for tree in a['trees']:
            nodes = np.zeros(len(x), dtype=int)
            left, right = np.array(tree['left']), np.array(tree['right'])
            feat, cut = np.array(tree['feature']), np.array(tree['threshold'])
            while (left[nodes] != -1).any():
                active = np.flatnonzero(left[nodes] != -1)
                n = nodes[active]
                nodes[active] = np.where(x[active, feat[n]] <= cut[n], left[n], right[n])
            outputs.append(np.array(tree['probability'])[nodes])
        p = np.mean(outputs, axis=0)
    p = np.clip(p, 1e-9, 1-1e-9)
    z = a['calibration']['slope'] * np.log(p/(1-p)) + a['calibration']['intercept']
    return 1/(1+np.exp(-np.clip(z, -700, 700)))


def fit_cohort(d, groups, name, output):
    splits = [d.loc[d.Patient_ID.isin(g)].copy() for g in groups]
    fit = splits[0]
    numeric = [c for c in d.columns if c not in EXCLUDE and c not in CATEGORICAL]
    # Units remain the supplied CSV's units, with no undocumented conversion.
    categories = {c: sorted(fit[c].unique().tolist()) for c in CATEGORICAL}
    columns = numeric + [f'{c}={v}' for c, vs in categories.items() for v in vs]
    def design(s):
        return np.column_stack([s[numeric].to_numpy(float)] +
                               [(s[c] == v).to_numpy(float) for c, vs in categories.items() for v in vs])
    raw = [design(s) for s in splits]
    med = np.nanmedian(raw[0], axis=0)
    filled = np.where(np.isnan(raw[0]), med, raw[0])
    mean, scale = filled.mean(0), filled.std(0)
    scale[scale == 0] = 1
    xs = [np.column_stack(((np.where(np.isnan(x), med, x)-mean)/scale, np.isnan(x).astype(float))) for x in raw]
    ys = [s.Sepsis_Label.to_numpy(int) for s in splits]
    weights = [1/s.groupby('Patient_ID').Patient_ID.transform('size').to_numpy() for s in splits]
    candidates = {}
    fitted = {}
    for kind, model in {'logistic': LogisticRegression(max_iter=2000, random_state=SEED),
                        'forest': RandomForestClassifier(n_estimators=150, max_depth=10, min_samples_leaf=15, n_jobs=2, random_state=SEED)}.items():
        model.fit(xs[0], ys[0], sample_weight=weights[0])
        def logits(x):
            p = np.clip(model.predict_proba(x)[:, 1], 1e-9, 1-1e-9)
            return np.log(p/(1-p)).reshape(-1, 1)
        calibrator = LogisticRegression(C=1e6, max_iter=2000).fit(logits(xs[1]), ys[1], sample_weight=weights[1])
        vp, tp = [calibrator.predict_proba(logits(x))[:, 1] for x in xs[2:]]
        threshold = float(np.quantile(vp[ys[2] == 1], .05))
        artifact = {'feature_version': 'supplied-neonatal-label-research-v1', 'model_version': f'{name}-{kind}-seed31',
                    'kind': kind, 'target': 'supplied observation-associated Sepsis_Label',
                    'clinical_eos_eligible': False, 'validation_status': 'research_only',
                    'numeric_columns': numeric, 'categories': categories, 'features': columns,
                    'median': med.tolist(), 'mean': mean.tolist(), 'scale': scale.tolist(),
                    'calibration': {'slope': float(calibrator.coef_[0, 0]), 'intercept': float(calibrator.intercept_[0])},
                    **export_estimator(model, kind)}
        np.testing.assert_allclose(portable_probability(artifact, xs[3]), tp, atol=1e-7)
        tmetrics = metrics(ys[3], tp, threshold)
        tmetrics.update(accuracy=float(accuracy_score(ys[3], tp >= threshold)), f1=float(f1_score(ys[3], tp >= threshold)))
        candidates[kind] = {'validation': metrics(ys[2], vp, threshold), 'test': tmetrics}
        fitted[kind] = (artifact, tp, threshold)
    chosen = min(candidates, key=lambda k: candidates[k]['validation']['brier'])
    artifact, tp, threshold = fitted[chosen]
    prior = np.full(len(ys[3]), np.average(ys[0], weights=weights[0]))
    report = {'cohort': name, 'selection': 'Lowest validation Brier among logistic and forest; test untouched until final reporting',
              'split': 'patient-ID-disjoint random 55/15/15/15, seed 31; NOT temporal',
              'partitions': [{'name': n, 'rows': len(s), 'patient_ids': int(s.Patient_ID.nunique()), 'positive_rows': int(s.Sepsis_Label.sum())} for n, s in zip(['fit','calibration','validation','test'], splits)],
              'features': columns, 'longitudinal_features': False, 'candidates': candidates, 'selected': chosen,
              'selected_test_cluster_bootstrap_95ci': bootstrap(ys[3], tp, splits[3].Patient_ID.to_numpy(), threshold),
              'bootstrap_repeats': 300, 'prior_baseline_test': metrics(ys[3], prior, .5),
              'clinical_eos_eligible': False, 'portable_parity_atol': 1e-7}
    save(output / name / 'model.json', artifact)
    save(output / name / 'evaluation.json', report)
    digest = hashlib.sha256((output/name/'model.json').read_bytes()).hexdigest()
    (output/name/'model.sha256').write_text(digest+'\n', encoding='ascii')
    return report


def run(archive, output):
    with ZipFile(archive) as z:
        # Read exactly the known member, never extract arbitrary archive paths.
        raw = z.read('Neonatal_Sepsis.csv')
    import io
    d = pd.read_csv(io.BytesIO(raw))
    if not set(d.Sepsis_Label.unique()) <= {0, 1}:
        raise ValueError('Expected binary supplied labels')
    report = audit(d, hashlib.sha256(raw).hexdigest())
    save(output/'data_audit.json', report)
    groups = partitions(d)
    reports = [fit_cohort(d, groups, 'all_neonatal_ages', output),
               fit_cohort(d.loc[d.Postnatal_Age.between(0, 2)], groups, 'postnatal_days_0_2', output)]
    save(output/'ml_summary.json', {'audit': report, 'experiments': reports,
         'packages': {k: importlib.metadata.version(k) for k in ['numpy','pandas','scikit-learn']}, 'seed': SEED})
    print(json.dumps({'audit': report, 'models': [{'cohort': r['cohort'], 'selected': r['selected'], 'test': r['candidates'][r['selected']]['test']} for r in reports]}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    run(a.archive, a.output)
