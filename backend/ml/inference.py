"""Immutable, digest-pinned JSON artifacts; never deserialize executable pickle."""
from __future__ import annotations

import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path

from ml.features import FEATURE_NAMES, FEATURE_VERSION, PredictionRequest, extract_features


def sigmoid(z):
    return 1 / (1 + math.exp(-max(-700, min(700, z))))


class ModelUnavailable(ValueError):
    pass


class PortableModel:
    def __init__(self, artifact: dict):
        self.artifact = artifact
        if artifact.get("feature_version") != FEATURE_VERSION or artifact.get("kind") not in {"logistic", "forest"}:
            raise ModelUnavailable("Unsupported model contract")
        self.names = artifact["features"]
        if not self.names or len(set(self.names)) != len(self.names) or not set(self.names) <= set(FEATURE_NAMES):
            raise ModelUnavailable("Invalid model features")
        n = len(self.names)
        if any(len(artifact[k]) != n for k in ("median", "mean", "scale", "ranges")):
            raise ModelUnavailable("Invalid preprocessing dimensions")
        if any(not math.isfinite(float(x)) for k in ("median", "mean", "scale") for x in artifact[k]):
            raise ModelUnavailable("Non-finite preprocessing")
        if any(x <= 0 for x in artifact["scale"]):
            raise ModelUnavailable("Invalid scaling")
        if artifact["kind"] == "logistic" and len(artifact["coefficients"]) != 2 * n:
            raise ModelUnavailable("Invalid coefficient dimensions")
        if artifact.get("validation_status") not in {"research_only", "clinically_approved"} or not artifact.get("model_version"):
            raise ModelUnavailable("Missing model lifecycle metadata")
        for key in ("min_ga", "max_ga", "min_age_hours", "max_age_hours"):
            if not math.isfinite(float(artifact["scope"][key])):
                raise ModelUnavailable("Invalid model scope")
        if not 0 <= artifact.get("max_missing_fraction", .5) <= 1:
            raise ModelUnavailable("Invalid missingness limit")
        for bounds in artifact["ranges"]:
            if len(bounds) != 2 or not all(math.isfinite(float(v)) for v in bounds) or bounds[0] > bounds[1]:
                raise ModelUnavailable("Invalid training support bounds")
        if not all(math.isfinite(float(artifact["calibration"][k])) for k in ("slope", "intercept")):
            raise ModelUnavailable("Invalid calibration")
        if artifact["kind"] == "logistic":
            if not all(math.isfinite(float(v)) for v in [artifact["intercept"], *artifact["coefficients"]]):
                raise ModelUnavailable("Non-finite coefficients")
        else:
            if not artifact.get("trees") or len(artifact["trees"]) > 1000:
                raise ModelUnavailable("Invalid tree ensemble")
            for tree in artifact["trees"]:
                size = len(tree["left"])
                if not 0 < size <= 100000 or any(len(tree[k]) != size for k in ("right", "feature", "threshold", "probability")):
                    raise ModelUnavailable("Invalid tree dimensions")
                for node in range(size):
                    if not math.isfinite(tree["threshold"][node]) or not 0 <= tree["probability"][node] <= 1:
                        raise ModelUnavailable("Invalid tree values")
                    if tree["left"][node] != -1 and not (0 <= tree["feature"][node] < 2*n and node < tree["left"][node] < size and node < tree["right"][node] < size):
                        raise ModelUnavailable("Invalid tree branches")

    def transform(self, features):
        a = self.artifact
        xs = [features.get(k) for k in self.names]
        missing = [float(x is None) for x in xs]
        imputed = [a["median"][i] if x is None else x for i, x in enumerate(xs)]
        scaled = [(x - a["mean"][i]) / a["scale"][i] for i, x in enumerate(imputed)]
        return scaled + missing, sum(missing) / len(missing)

    def raw_probability(self, transformed):
        a = self.artifact
        if a["kind"] == "logistic":
            return sigmoid(a["intercept"] + sum(c * x for c, x in zip(a["coefficients"], transformed)))
        probs = []
        # Match sklearn's tree input dtype, including threshold-edge cases.
        transformed = [struct.unpack('f', struct.pack('f', v))[0] for v in transformed]
        for tree in a["trees"]:
            node = 0
            for _ in range(len(tree["left"]) + 1):
                if tree["left"][node] == -1:
                    probs.append(tree["probability"][node])
                    break
                node = tree["left"][node] if transformed[tree["feature"][node]] <= tree["threshold"][node] else tree["right"][node]
            else:
                raise ModelUnavailable("Invalid tree traversal")
        if not probs:
            raise ModelUnavailable("Empty forest")
        return sum(probs) / len(probs)

    def probability(self, transformed):
        p = max(1e-9, min(1 - 1e-9, self.raw_probability(transformed)))
        a = self.artifact["calibration"]
        return sigmoid(a["slope"] * math.log(p / (1 - p)) + a["intercept"])

    def predict(self, request: PredictionRequest):
        features = extract_features(request)
        x, missing_fraction = self.transform(features)
        a = self.artifact
        scope = a["scope"]
        ga = request.current.values.get("gestational_age_weeks")
        reasons = []
        if ga is None or not scope["min_ga"] <= ga <= scope["max_ga"]:
            reasons.append("Gestational age is missing or outside the development cohort")
        if not scope["min_age_hours"] <= request.current.age_hours <= scope["max_age_hours"]:
            reasons.append("Prediction age is outside the development cohort")
        if missing_fraction > a.get("max_missing_fraction", 0.5):
            reasons.append("Too many model predictors are missing")
        out_of_range = [k for i, k in enumerate(self.names) if features[k] is not None and not a["ranges"][i][0] <= features[k] <= a["ranges"][i][1]]
        if out_of_range:
            reasons.append("Predictors outside training support: " + ", ".join(out_of_range))
        common = {"model_version": a["model_version"], "missing_fraction": missing_fraction,
                  "validation_status": a["validation_status"], "feature_version": FEATURE_VERSION,
                  "clinical_use": request.purpose == "clinical", "warnings": reasons,
                  "contribution_method": "standardized log-odds" if a["kind"] == "logistic" else "median replacement probability difference"}
        if reasons:
            return {**common, "status": "abstained", "probability_per_1000": None, "contributions": []}
        p = self.probability(x)
        if a["kind"] == "logistic":
            contributions = [{"feature": name, "value": features[name], "contribution": a["coefficients"][i] * x[i] + a["coefficients"][i + len(self.names)] * x[i + len(self.names)]} for i, name in enumerate(self.names)]
        else:
            contributions = []
            for i, name in enumerate(self.names):
                replaced = x.copy()
                replaced[i] = (a["median"][i] - a["mean"][i]) / a["scale"][i]
                contributions.append({"feature": name, "value": features[name], "contribution": p - self.probability(replaced)})
        return {**common, "status": "predicted", "probability_per_1000": round(p * 1000, 6),
                "contributions": sorted(contributions, key=lambda c: abs(c["contribution"]), reverse=True)[:10],
                "warnings": ["Research model; local prospective validation is required."] if request.purpose == "research" else []}


@lru_cache(maxsize=4)
def load_model(path: str, expected_sha256: str) -> PortableModel:
    if not expected_sha256:
        raise ModelUnavailable("MODEL_ARTIFACT_SHA256 must pin the reviewed artifact")
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise ModelUnavailable("No trained EOS model artifact is installed") from e
    if len(raw) > 20_000_000 or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ModelUnavailable("EOS model digest mismatch")
    try:
        return PortableModel(json.loads(raw))
    except (KeyError, TypeError, ValueError) as e:
        raise ModelUnavailable("Invalid EOS model artifact") from e


def model_status(settings):
    try:
        m = load_model(settings.model_artifact_path, settings.model_artifact_sha256)
        approved = m.artifact.get("validation_status") == "clinically_approved"
        return {"available": True, "version": m.artifact["model_version"], "clinical_ready": approved and settings.clinical_use_enabled}
    except ModelUnavailable as e:
        return {"available": False, "clinical_ready": False, "reason": str(e)}


def predict(request, settings):
    model = load_model(settings.model_artifact_path, settings.model_artifact_sha256)
    if request.purpose == "clinical" and (not settings.clinical_use_enabled or model.artifact.get("validation_status") != "clinically_approved"):
        raise ModelUnavailable("Clinical inference requires an approved model and CLINICAL_USE_ENABLED")
    return model.predict(request)
