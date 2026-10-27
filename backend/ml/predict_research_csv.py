"""Batch inference for supplied-label research artifacts; not the EOS API.

Output contains row ordinal and supplied-label probability, never patient IDs.
The artifact digest must be supplied explicitly. No executable serialization.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.research_cohort import portable_probability


def predict_csv(model_path, digest, csv_path, output):
    raw = model_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Research artifact digest mismatch')
    a = json.loads(raw)
    if a.get('feature_version') != 'supplied-neonatal-label-research-v1' or a.get('clinical_eos_eligible') is not False:
        raise ValueError('Expected a supplied-label research artifact')
    data = pd.read_csv(csv_path)
    numeric = data[a['numeric_columns']].apply(pd.to_numeric, errors='raise')
    if np.isinf(numeric.to_numpy(float)).any():
        raise ValueError('Infinite inputs are not accepted')
    for c, values in a['categories'].items():
        if not data[c].isin(values).all():
            raise ValueError('Unknown categorical input: '+c)
    x = np.column_stack([numeric.to_numpy(float)] + [(data[c] == v).to_numpy(float) for c, values in a['categories'].items() for v in values])
    missing = np.isnan(x)
    x = np.column_stack(((np.where(missing,a['median'],x)-a['mean'])/a['scale'],missing.astype(float)))
    probabilities = portable_probability(a,x)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({'row_ordinal':np.arange(len(data)), 'supplied_label_probability': probabilities,
                  'clinical_eos_eligible':False, 'target':'supplied Sepsis_Label; research only'}).to_csv(output,index=False)
    return len(data)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--sha256',required=True)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print({'rows':predict_csv(a.model,a.sha256,a.input,a.output),'clinical_eos_eligible':False})
