"""Train on adjudicated JSONL landmarks. Usage: python -m ml.train --help

Four patient-disjoint temporal partitions: fit, calibration, selection, test.
Test metrics never select the model. Exports portable LR/forest JSON only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score, confusion_matrix

from ml.features import FEATURE_NAMES, FEATURE_VERSION, PredictionRequest, extract_features
from ml.inference import PortableModel


def partition(records):
    births = {}
    for r in records:
        patient = str(r["patient_id"])
        if patient in births and births[patient] != r["birth_time"]:
            raise ValueError("A patient has inconsistent birth times")
        births[patient] = r["birth_time"]
    # MIMIC's subject-specific date shifts do not preserve real calendar time.
    # Its adapter supplies split_time from ADMISSIONS.ADMITTIME only for audit;
    # use deterministic patient hashing for MIMIC, never claim temporal validation.
    mimic = all(r.get("source") == "mimiciii-1.4" for r in records)
    ids = sorted(births, key=(lambda p: hashlib.sha256(("eos-split-v1:" + p).encode()).hexdigest()) if mimic else lambda p: births[p])
    cuts = [0, int(len(ids) * .55), int(len(ids) * .70), int(len(ids) * .85), len(ids)]
    groups = [set(ids[cuts[i]:cuts[i + 1]]) for i in range(4)]
    splits = [[r for r in records if str(r["patient_id"]) in g] for g in groups]
    # For real unshifted times do not let tied birth dates cross a boundary.
    if not mimic:
        for left, right in zip(splits, splits[1:]):
            if left and right and max(r["birth_time"] for r in left) >= min(r["birth_time"] for r in right):
                raise ValueError("Temporal boundary has tied birth times; supply precise birth times or predefined external cohorts")
    for split in splits:
        counts = np.bincount([r["label"] for r in split], minlength=2)
        # Engineering floor only; this is far below clinical validation needs.
        if min(counts) < 5:
            raise ValueError("Every partition needs >=5 positive and negative landmarks; collect more EOS outcomes")
    return splits, "patient-hash (dates shifted; NOT temporal validation)" if mimic else "patient-disjoint temporal"


def matrix(records, names):
    return np.array([[extract_features(PredictionRequest.model_validate(r["prediction"]))[n] for n in names] for r in records], dtype=float)


def metrics(y, p, threshold):
    tn, fp, fn, tp = confusion_matrix(y, p >= threshold, labels=[0, 1]).ravel()
    # Reliability bins show calibration without implying a clinical decision threshold.
    bins = []
    for lo, hi in zip(np.linspace(0, 1, 11)[:-1], np.linspace(0, 1, 11)[1:]):
        mask = (p >= lo) & (p <= hi if hi == 1 else p < hi)
        if mask.any():
            bins.append({"n": int(mask.sum()), "predicted": float(p[mask].mean()), "observed": float(y[mask].mean())})
    return {"n": len(y), "positive": int(sum(y)), "prevalence": float(np.mean(y)),
            "auroc": float(roc_auc_score(y, p)), "auprc": float(average_precision_score(y, p)),
            "brier": float(brier_score_loss(y, p)), "sensitivity": float(tp / (tp + fn)),
            "specificity": float(tn / (tn + fp)), "ppv": float(tp / (tp + fp)) if tp + fp else None,
            "threshold": float(threshold), "calibration_bins": bins}


def export_estimator(estimator, kind):
    if kind == "logistic":
        return {"coefficients": estimator.coef_[0].tolist(), "intercept": float(estimator.intercept_[0])}
    trees = []
    for est in estimator.estimators_:
        t = est.tree_
        values = t.value[:, 0, :]
        probs = values[:, 1] / values.sum(axis=1)
        trees.append({"left": t.children_left.tolist(), "right": t.children_right.tolist(),
                      "feature": t.feature.tolist(), "threshold": t.threshold.tolist(), "probability": probs.tolist()})
    return {"trees": trees}


def train(path: Path, output: Path):
    raw = path.read_bytes()
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not records:
        raise ValueError("Empty cohort")
    for r in records:
        if type(r.get("label")) is not int or r.get("label") not in (0, 1) or r.get("label_adjudicated") is not True:
            raise ValueError("Only adjudicated binary EOS labels may enter training")
        if r.get("synthetic") or not r.get("source"):
            raise ValueError("Synthetic or unprovenanced data cannot be exported as an EOS model")
        PredictionRequest.model_validate(r["prediction"])
        if r.get("culture_collection_age_hours") is not None and r["prediction"]["current"]["age_hours"] >= r["culture_collection_age_hours"]:
            raise ValueError("Prediction must precede diagnostic culture collection")
    splits, split_method = partition(records)
    fit, cal, val, test = splits
    full = matrix(fit, FEATURE_NAMES)
    # Remove constants and predictors absent in >=80% of the training cohort.
    selected = [i for i in range(full.shape[1]) if np.isfinite(full[:, i]).mean() >= .2 and np.nanstd(full[:, i]) > 0]
    names = [FEATURE_NAMES[i] for i in selected]
    if len(names) < 2:
        raise ValueError("Insufficient usable predictors")
    xfit = full[:, selected]
    median = np.nanmedian(xfit, axis=0)
    imputed = np.where(np.isnan(xfit), median, xfit)
    mean, scale = imputed.mean(axis=0), imputed.std(axis=0)
    scale[scale == 0] = 1
    xs = []
    ys = []
    for split in splits:
        x = matrix(split, names)
        xs.append(np.hstack(((np.where(np.isnan(x), median, x) - mean) / scale, np.isnan(x).astype(float))))
        ys.append(np.array([r["label"] for r in split]))
    # Equal weight per patient despite different numbers of landmarks.
    def weights(split):
        counts = {}
        for r in split:
            counts[r["patient_id"]] = counts.get(r["patient_id"], 0) + 1
        return np.array([1 / counts[r["patient_id"]] for r in split])
    candidates = {}
    for kind, estimator in {
        "logistic": LogisticRegression(C=1.0, max_iter=2000, random_state=31),
        "forest": RandomForestClassifier(n_estimators=100, max_depth=6, min_samples_leaf=10, random_state=31, n_jobs=1),
    }.items():
        estimator.fit(xs[0], ys[0], sample_weight=weights(fit))
        cal_prob = np.clip(estimator.predict_proba(xs[1])[:, 1], 1e-9, 1 - 1e-9)
        logits = np.log(cal_prob / (1 - cal_prob)).reshape(-1, 1)
        calibrator = LogisticRegression(C=1e6, max_iter=2000).fit(logits, ys[1], sample_weight=weights(cal))
        def probability(x):
            p = np.clip(estimator.predict_proba(x)[:, 1], 1e-9, 1 - 1e-9)
            return calibrator.predict_proba(np.log(p / (1 - p)).reshape(-1, 1))[:, 1]
        vp = probability(xs[2])
        # Research operating point chosen on validation only; never treatment guidance.
        positives = np.sort(vp[ys[2] == 1])
        threshold = float(positives[max(0, int(len(positives) * .05) - 1)])
        observations = [PredictionRequest.model_validate(r["prediction"]).current for r in fit]
        gas = [o.values.get("gestational_age_weeks") for o in observations if o.values.get("gestational_age_weeks") is not None]
        if not gas:
            raise ValueError("Gestational age must be measured/adjudicated; no implicit term classification")
        artifact = {"model_version": f"eos-{kind}-{hashlib.sha256(raw).hexdigest()[:12]}", "kind": kind,
                    "feature_version": FEATURE_VERSION, "features": names,
                    "median": median.tolist(), "mean": mean.tolist(), "scale": scale.tolist(),
                    "ranges": [[float(np.nanmin(xfit[:, i])), float(np.nanmax(xfit[:, i]))] for i in range(len(names))],
                    "calibration": {"slope": float(calibrator.coef_[0, 0]), "intercept": float(calibrator.intercept_[0])},
                    "scope": {"min_ga": min(gas), "max_ga": max(gas), "min_age_hours": min(o.age_hours for o in observations), "max_age_hours": max(o.age_hours for o in observations)},
                    "validation_status": "research_only", "max_missing_fraction": .5,
                    "training_data_sha256": hashlib.sha256(raw).hexdigest(), **export_estimator(estimator, kind)}
        portable = PortableModel(artifact)
        # Numerical parity before export, including calibration and tree leaves.
        np.testing.assert_allclose([portable.probability(x.tolist()) for x in xs[2]], vp, atol=1e-7)
        candidates[kind] = {"artifact": artifact, "validation": metrics(ys[2], vp, threshold), "test_p": probability(xs[3]), "threshold": threshold}
    chosen = min(candidates, key=lambda k: candidates[k]["validation"]["brier"])
    winner = candidates[chosen]
    report = {"status": "research_only", "split_method": split_method, "selection_metric": "validation Brier score",
              "selected": chosen, "candidate_validation": {k: v["validation"] for k, v in candidates.items()},
              "test": metrics(ys[3], winner["test_p"], winner["threshold"]),
              "partitions": [{"patients": len({r["patient_id"] for r in s}), "landmarks": len(s)} for s in splits],
              "limitations": ["Retrospective single-dataset results do not establish clinical utility", "Landmark metrics are correlated within patient; patient bootstrap and external validation required", "Research operating point is not a treatment threshold"]}
    output.mkdir(parents=True, exist_ok=True)
    model_bytes = (json.dumps(winner["artifact"], indent=2, allow_nan=False) + "\n").encode()
    (output / "model.json").write_bytes(model_bytes)
    (output / "evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "model.sha256").write_text(hashlib.sha256(model_bytes).hexdigest() + "\n", encoding="ascii")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("ml/artifacts"))
    args = parser.parse_args()
    print(json.dumps(train(args.data, args.output), indent=2))
