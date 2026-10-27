"""Independent diagnostics of the supplied-label models; never clinical approval.

The original test partition has already been reported. These are post-hoc audit
and stress analyses, not a newly untouched test or evidence of future prediction.
"""
import io,json,hashlib,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,brier_score_loss,average_precision_score
from sklearn.neighbors import NearestNeighbors

from ml.research_cohort import partitions,portable_probability,save,CATEGORICAL,EXCLUDE

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/research/leakage_audit'


def stats(y,p):
    return {'n':len(y),'auroc':float(roc_auc_score(y,p)),
            'auprc':float(average_precision_score(y,p)),'brier':float(brier_score_loss(y,p))}


def design(d,a):
    raw=np.column_stack([d[a['numeric_columns']].to_numpy(float)]+
                        [(d[c]==v).to_numpy(float) for c,vs in a['categories'].items() for v in vs])
    return np.column_stack(((np.where(np.isnan(raw),a['median'],raw)-a['mean'])/a['scale'],np.isnan(raw).astype(float)))


def run():
    with zipfile.ZipFile(r'C:\Users\hadia\Downloads\archive (1).zip') as z:raw=z.read('Neonatal_Sepsis.csv')
    d=pd.read_csv(io.BytesIO(raw));groups=partitions(d)
    report={'csv_sha256':hashlib.sha256(raw).hexdigest(),'analysis_role':'post-hoc audit; test partition previously reported',
            'patient_split_overlap':{f'{i}-{j}':len(groups[i]&groups[j]) for i in range(4) for j in range(i)},
            'label_is_explicit_predictor':False,'preprocessing_partition':'fit only','experiments':{}}
    for name,cohort in [('all_neonatal_ages',d),('postnatal_days_0_2',d.loc[d.Postnatal_Age.between(0,2)])]:
        a=json.loads((ROOT/'output/research'/name/'model.json').read_text())
        splits=[cohort.loc[cohort.Patient_ID.isin(g)].copy() for g in groups]
        xs=[design(s,a) for s in splits];ys=[s.Sepsis_Label.to_numpy(int) for s in splits]
        raw_fit=np.column_stack([splits[0][a['numeric_columns']].to_numpy(float)]+
                    [(splits[0][c]==v).to_numpy(float) for c,vs in a['categories'].items() for v in vs])
        med=np.nanmedian(raw_fit,axis=0);filled=np.where(np.isnan(raw_fit),med,raw_fit)
        scale=filled.std(axis=0);scale[scale==0]=1
        for actual,expected in [(a['median'],med),(a['mean'],filled.mean(axis=0)),(a['scale'],scale)]:
            np.testing.assert_allclose(actual,expected,atol=1e-10)
        assert not any(n.split('=')[0] in EXCLUDE for n in a['features'])
        fitted=[stats(y,portable_probability(a,x)) for x,y in zip(xs,ys)]
        # Exact duplicate detection ignores ID, hour and label. Also inspect rows
        # whose predictor vector is duplicated under a different supplied ID.
        feature_cols=[c for c in cohort.columns if c not in EXCLUDE]
        hashes=[set(pd.util.hash_pandas_object(s[feature_cols],index=False).tolist()) for s in splits]
        overlaps={f'{i}-{j}':len(hashes[i]&hashes[j]) for i in range(4) for j in range(i)}
        exact_duplicates=int(cohort[feature_cols].duplicated().sum())
        ablations={}
        feature_sets={
            'all_predictors':[c for c in feature_cols],
            'without_PCT':[c for c in feature_cols if c!='PCT'],
            'without_CRP_PCT':[c for c in feature_cols if c not in ['CRP','PCT']],
            'baseline_only':['Gestational_Age','Birth_Weight','Sex','Postnatal_Age','Delivery_Mode','Apgar'],
            'vitals_without_laboratory':['Gestational_Age','Birth_Weight','Sex','Postnatal_Age','Delivery_Mode','Apgar','HR','Resp','Temp','SpO2','BP'],
            'laboratory_only':['WBC','CRP','PCT','Platelets','Lactate','Hemoglobin'],
        }
        for label,columns in feature_sets.items():
            selected=[i for i,n in enumerate(a['features']) if n.split('=')[0] in columns]
            selected+= [i+len(a['features']) for i in selected]
            xfit,xtest=xs[0][:,selected],xs[3][:,selected]
            model=LogisticRegression(max_iter=1500,random_state=31).fit(xfit,ys[0])
            ablations[label]={'features':columns,'fit':stats(ys[0],model.predict_proba(xfit)[:,1]),
                              'test':stats(ys[3],model.predict_proba(xtest)[:,1]),'calibration':'none; discrimination diagnostic only'}
        rng=np.random.default_rng(113)
        negative=[]
        for seed in [113,114,115]:
            permuted=np.random.default_rng(seed).permutation(ys[0])
            model=LogisticRegression(max_iter=1000,random_state=seed).fit(xs[0],permuted)
            prediction=model.predict_proba(xs[3])[:,1]
            permuted_test=np.random.default_rng(seed+1000).permutation(ys[3])
            negative.append({'seed':seed,'permuted_test_labels':stats(permuted_test,prediction),
                             'original_test_labels':stats(ys[3],prediction)})
        # Numeric/categorical nearest neighbors on the same fit-only scaling;
        # sample queries for bounded memory/time and never label these an
        # exhaustive near-duplicate search or an independence proof.
        n=min(1000,len(xs[3]));ix=rng.choice(len(xs[3]),n,replace=False)
        neighbor=NearestNeighbors(n_neighbors=1,algorithm='ball_tree',n_jobs=2).fit(xs[0])
        distances,_=neighbor.kneighbors(xs[3][ix])
        nearest={'sampled_test_rows':n,'standardized_euclidean_quantiles':np.quantile(distances[:,0],[0,.01,.05,.5,.95,1]).tolist(),
                 'distance_below_1e_6':int((distances[:,0]<1e-6).sum()),'exhaustive':False}
        # Unit-scale changes are a real integration risk: never apply these as
        # clinical conversions. This stress test shows model input sensitivity.
        stresses={}
        for field,factor in [('WBC',1000),('Platelets',1000),('Birth_Weight',1000)]:
            corrupted=splits[3].copy();corrupted[field]*=factor
            stresses[field+'_wrong_scale_x1000']=stats(ys[3],portable_probability(a,design(corrupted,a)))
        report['experiments'][name]={
            'selected_forest_partitions':dict(zip(['fit','calibration','validation','test'],fitted)),
            'fit_minus_test_auroc':fitted[0]['auroc']-fitted[3]['auroc'],
            'exact_predictor_duplicates':exact_duplicates,'exact_predictor_split_overlap':overlaps,
            'preprocessing_recomputed_from_fit_matches':True,
            'label_permutation_negative_controls':negative,'feature_ablations_logistic':ablations,
            'nearest_neighbor_diagnostic':nearest,'wrong_unit_scale_stresses':stresses,
            'label_timestamp_available':False,'clinical_eos_eligible':False,
        }
        print('audited',name,flush=True)
    report['interpretation_limits']=[
        'Patient-ID and exact-row checks cannot establish independence when supplied identities are inconsistent',
        'No onset or result-availability timestamps: concurrent label proxies and diagnostic workflow leakage cannot be ruled out',
        'Strong discrimination or a small train/test gap does not establish a clinically meaningful or externally valid outcome',
        'Random-label performance near chance checks pipeline behavior, not the provenance or correctness of real labels',
        'Ablations are post-hoc on the previously reported test; they do not select a clinically released model',
    ]
    save(OUT/'audit.json',report)
    print(json.dumps({'report':str(OUT/'audit.json'),'clinical_eos_eligible':False}))


if __name__=='__main__':run()
