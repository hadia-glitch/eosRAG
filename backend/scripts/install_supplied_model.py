"""Package the actually trained days-0-2 model for authenticated research serving.
Development-support ranges use the FIT partition only. Source labels stay unapproved.
"""
import hashlib,json,zipfile,io
from pathlib import Path
import pandas as pd
from ml.research_cohort import partitions
from ml.supplied_model import NUMERIC,load_supplied_model

if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    source=root/'output/research/postnatal_days_0_2/model.json'
    target=root/'backend/ml/deployed/supplied_neonatal';target.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(Path.home()/'Downloads/archive (1).zip') as z:raw=z.read('Neonatal_Sepsis.csv')
    d=pd.read_csv(io.BytesIO(raw));fit_ids=partitions(d)[0]
    fit=d.loc[d.Patient_ID.isin(fit_ids)&d.Postnatal_Age.between(0,2)]
    missing_limit=int(fit[NUMERIC].isna().sum(axis=1).quantile(.995,interpolation='higher'))
    scope={'ranges':{k:[float(fit[k].min()),float(fit[k].max())] for k in NUMERIC},'max_missing_predictors':missing_limit,
           'missingness_policy':'fit-partition 99.5th percentile of missing predictor counts','partition':'fit only','min_age_hours':0,'max_age_hours_exclusive':72,'clinical_eos_eligible':False,
           'training_csv_sha256':hashlib.sha256(raw).hexdigest(),'units_verified':False}
    (target/'model.json').write_bytes(source.read_bytes())
    (target/'scope.json').write_text(json.dumps(scope,indent=2)+'\n',encoding='utf8')
    manifest={'purpose':'Supplied-label research inference only','sha256':{n:hashlib.sha256((target/n).read_bytes()).hexdigest() for n in ['model.json','scope.json']}}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    model=load_supplied_model(str(target))
    print({'installed':True,'model_version':model.a['model_version'],'clinical_ready':False,'sha256':manifest['sha256']['model.json']})
