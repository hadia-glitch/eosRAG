"""Stream local MIMIC-III CSV(.gz) tables; never download credentials/data.

prepare_mimic review produces a neonatal review template and item catalog.
prepare_mimic build requires adjudicated birth times, GA, labels and a reviewed
item/unit map. It does not equate negative/missing cultures with no sepsis.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from ml.features import NUMERIC, PredictionRequest


def rows(root: Path, table: str):
    path = next((p for name in (f"{table}.csv.gz", f"{table}.csv", f"{table.lower()}.csv.gz", f"{table.lower()}.csv") if (p := root / name).exists()), None)
    if path is None:
        raise ValueError(f"Missing table: {table}")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def parse_time(value):
    return datetime.fromisoformat(value)


def neonatal_admissions(root):
    # Admission type is a candidate filter only. Reviewer confirms birth/age.
    return {r["HADM_ID"]: r for r in rows(root, "ADMISSIONS") if r.get("ADMISSION_TYPE", "").upper() == "NEWBORN"}


def review(root, output):
    output.mkdir(parents=True, exist_ok=True)
    admissions = neonatal_admissions(root)
    cultures = defaultdict(list)
    for r in rows(root, "MICROBIOLOGYEVENTS"):
        if r.get("HADM_ID") in admissions and "BLOOD" in r.get("SPEC_TYPE_DESC", "").upper():
            cultures[r["HADM_ID"]].append({k: r.get(k) for k in ("CHARTDATE", "CHARTTIME", "ORG_NAME", "SPEC_TYPE_DESC")})
    with (output / "adjudication_template.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["subject_id", "hadm_id", "birth_time", "gestational_age_weeks", "birth_weight_g", "label", "label_adjudicated", "culture_collection_age_hours", "followup_hours", "reviewer"])
        writer.writeheader()
        for hadm, r in admissions.items():
            writer.writerow({"subject_id": r["SUBJECT_ID"], "hadm_id": hadm, "label_adjudicated": "false"})
    (output / "blood_culture_review.json").write_text(json.dumps(cultures, indent=2), encoding="utf-8")
    with (output / "item_catalog.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["table", "itemid", "label", "unit"])
        writer.writeheader()
        for table in ("D_ITEMS", "D_LABITEMS"):
            for r in rows(root, table):
                writer.writerow({"table": "CHARTEVENTS" if table == "D_ITEMS" else "LABEVENTS", "itemid": r["ITEMID"], "label": r.get("LABEL"), "unit": r.get("UNITNAME", "")})
    return {"candidate_admissions": len(admissions), "status": "clinical_adjudication_required"}


def build(root, adjudications, mapping_path, output):
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if not mapping.get("reviewed_by") or not mapping.get("reviewed_at"):
        raise ValueError("Item/unit map requires documented review")
    patients = {}
    with adjudications.open(encoding="utf-8-sig", newline="") as stream:
        for r in csv.DictReader(stream):
            if r["label_adjudicated"].lower() != "true":
                continue
            if not r.get("reviewer") or r["label"] not in {"0", "1"} or not r.get("birth_time"):
                raise ValueError("Incomplete adjudication")
            if float(r["followup_hours"]) < 72:
                raise ValueError("72-hour outcome ascertainment required")
            parse_time(r["birth_time"])
            patients[r["hadm_id"]] = r
    events = defaultdict(list)
    excluded = defaultdict(int)
    for table in ("CHARTEVENTS", "LABEVENTS"):
        item_map = mapping.get(table, {})
        if not item_map:
            continue
        for r in rows(root, table):
            hadm, itemid = r.get("HADM_ID"), r.get("ITEMID")
            if hadm not in patients or itemid not in item_map:
                continue
            m = item_map[itemid]
            if m["feature"] not in NUMERIC or str(r.get("ERROR", "")) == "1":
                excluded["invalid_item_or_error"] += 1
                continue
            if r.get("VALUEUOM", "").strip().lower() != m["unit"].strip().lower():
                excluded["unit_mismatch"] += 1
                continue
            # CHARTEVENTS.STORETIME approximates availability. LABEVENTS has
            # no result availability time: exclude by default. An explicitly
            # reviewed latency assumption may be supplied for sensitivity work.
            chart = r.get("CHARTTIME")
            stored = r.get("STORETIME")
            delay = m.get("availability_delay_hours")
            if not chart or (not stored and delay is None):
                excluded["unknown_availability"] += 1
                continue
            try:
                birth = parse_time(patients[hadm]["birth_time"])
                measured = (parse_time(chart) - birth).total_seconds() / 3600
                available = max(measured, (parse_time(stored) - birth).total_seconds() / 3600) if stored else measured + float(delay)
                value = float(r.get("VALUENUM", "")) * float(m.get("factor", 1)) + float(m.get("offset", 0))
                lo, hi = NUMERIC[m["feature"]]
                if not (0 <= measured <= available <= 72 and lo <= value <= hi):
                    raise ValueError("Out of range")
                events[hadm].append((available, measured, m["feature"], value))
            except (ValueError, TypeError):
                excluded["invalid_value_or_time"] += 1
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as stream:
        for hadm, r in patients.items():
            for landmark in (6, 12, 24, 36, 48):
                culture_age = float(r["culture_collection_age_hours"]) if r.get("culture_collection_age_hours") else None
                if culture_age is not None and landmark >= culture_age:
                    continue
                # Reconstruct successive landmarks using only information that
                # had arrived at each time. Never backfill a later result.
                observations = []
                for t in range(0, landmark + 1, 3):
                    values = {"gestational_age_weeks": float(r["gestational_age_weeks"])}
                    if r.get("birth_weight_g"):
                        values["birth_weight_g"] = float(r["birth_weight_g"])
                    # Freshness: no acute vital/lab is carried for >6 hours.
                    for available, measured, feature, value in sorted(events[hadm]):
                        if available <= t and 0 <= t - measured <= 6:
                            values[feature] = value
                    observations.append({"age_hours": t, "values": values})
                prediction = {"current": observations[-1], "history": observations[:-1], "purpose": "research"}
                PredictionRequest.model_validate(prediction)
                record = {"patient_id": hashlib.sha256(("mimiciii:" + r["subject_id"]).encode()).hexdigest(),
                          "birth_time": r["birth_time"], "source": "mimiciii-1.4", "label": int(r["label"]),
                          "label_adjudicated": True, "culture_collection_age_hours": culture_age, "prediction": prediction}
                stream.write(json.dumps(record, allow_nan=False) + "\n")
                count += 1
    report = {"landmarks": count, "adjudicated_admissions": len(patients), "excluded_events": dict(excluded),
              "mapping_sha256": hashlib.sha256(mapping_path.read_bytes()).hexdigest(),
              "adjudications_sha256": hashlib.sha256(adjudications.read_bytes()).hexdigest(),
              "limitations": ["MIMIC dates are shifted per patient: no real temporal split", "Single historical NICU cohort; not general birth-population EOS risk", "Availability delay assumptions require sensitivity analysis", "Culture review and EOS/contaminant adjudication remain clinician responsibilities"]}
    output.with_suffix(".provenance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["review", "build"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path)
    parser.add_argument("--item-map", type=Path)
    args = parser.parse_args()
    if args.mode == "review":
        print(json.dumps(review(args.root, args.output), indent=2))
    elif not args.adjudications or not args.item_map:
        parser.error("build requires --adjudications and --item-map")
    else:
        print(json.dumps(build(args.root, args.adjudications, args.item_map, args.output), indent=2))
