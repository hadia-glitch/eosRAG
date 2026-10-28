"""Paper-inspired NB/TAN ablation on the unchanged pre-culture PIC cohort.

The paper diagnoses broad paediatric sepsis using admission data. This experiment
keeps neonatal pre-culture prediction, patient-disjoint folds and the existing
unadjudicated outcome. It is not a reproduction or independent final test.
"""
import argparse,json,sys,csv
from pathlib import Path
import numpy as np
from sklearn.model_selection import StratifiedKFold

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from ml.dynamic_features import features,SNAPSHOT
from ml.temporal_bayes import TemporalBayes
from ml.pic_dataset import save,digest
from ml.train_pic_longitudinal import weighting,metrics,clustered_ci,write_csv

EXTRA=tuple(f'{k}__{s}' for k in ['neonatal_temperature','heart_rate','respiratory_rate','spo2']
            for s in ['slope_per_hour','delta','count','recency_hours'])
METHODS={'snapshot_nb':(False,SNAPSHOT),'snapshot_tan':(True,SNAPSHOT),
         'longitudinal_nb':(False,SNAPSHOT+EXTRA),'longitudinal_tan':(True,SNAPSHOT+EXTRA)}


def main():
    base=ROOT/'output/research/pic_longitudinal';out=base/'paper_inspired_bayes'
    private=ROOT/'data/picdb_private';raw=private/'landmarks.jsonl'
    rows=[json.loads(s) for s in raw.read_text().splitlines()]
    inherited=json.loads((base/'training_protocol.json').read_text())
    if digest(raw)!=inherited['cohort_sha256']:raise ValueError('Cohort changed')
    protocol={'stage':'development_only','source_paper':'https://doi.org/10.21037/tp-22-510',
        'paper_cohort_not_comparable':'Paediatric diagnosis using first 24h, discharge diagnoses/SIRS/infection and microbiology; not neonatal pre-culture EOS forecasting.',
        'cohort_sha256':digest(raw),'seeds':[31,47,83],'patient_folds':3,'primary_seed':31,
        'equivalent_sample_size':10.,'methods':{k:{'tree':t,'features':f} for k,(t,f) in METHODS.items()},
        'feature_selection':'Outcome-blind training-fold variation and >=5 distinct training infants with observations',
        'discretization':'Training-only binary/ternary midpoints or empirical terciles; separate missing state',
        'graph':'Conditional mutual information maximum spanning tree, deterministic root zero; no causal claim',
        'smoothing':'Global marginal prior -> class marginal -> class/parent conditional table; ESS10 fixed before scoring',
        'weights':'Equal total weight per training infant; all held-out landmarks stay with that infant',
        'no_imputed_patient_facts':True,'no_culture_or_later_outcome_predictors':True,
        'clinical_eos_eligible':False,'clinical_model_promotion':False,
        'resamples':2000,'bootstrap_unit':'infant','bootstrap_seed':31,
        'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'backend/ml/temporal_bayes.py',ROOT/'backend/ml/dynamic_features.py']}}
    target=out/'protocol.json'
    if target.exists() and json.loads(target.read_text())!=protocol:raise ValueError('Bayesian protocol drift')
    save(target,protocol)
    extracted=[features(r['index_age_hours'],r['sex'],r['events']) for r in rows]
    labels={r['patient_id']:r['label'] for r in rows};pids=np.array(sorted(labels));py=np.array([labels[p] for p in pids])
    y=np.array([r['label'] for r in rows]);w=weighting(rows);groups=np.array([r['patient_id'] for r in rows])
    results=[];predictions={};fold_counts=[]
    for seed in protocol['seeds']:
        folds=[]
        for fold,(tr,ho) in enumerate(StratifiedKFold(3,shuffle=True,random_state=seed).split(pids,py)):
            train=set(pids[tr]);test=set(pids[ho]);assert not train&test
            folds.append((np.flatnonzero(np.isin(groups,list(train))),np.flatnonzero(np.isin(groups,list(test)))))
            fold_counts.append({'seed':seed,'fold':fold,'training_infants':len(train),'test_infants':len(test),
                'training_positive_infants':int(py[tr].sum()),'test_positive_infants':int(py[ho].sum()),'overlap':0})
        for name,(tree,cols) in METHODS.items():
            x=np.array([[f[c] for c in cols] for f in extracted],dtype=float);p=np.zeros(len(rows));counts=[]
            for tr,ho in folds:
                keep=[]
                for j in range(x.shape[1]):
                    finite=np.isfinite(x[tr,j]);observed=set(groups[tr][finite])
                    if len(observed)>=5 and np.nanstd(x[tr,j])>0:keep.append(j)
                model=TemporalBayes(tree=tree,equivalent_sample_size=10.).fit(x[tr][:,keep],y[tr],weighting([rows[i] for i in tr]))
                p[ho]=model.predict_proba(x[ho][:,keep])[:,1];counts.append(len(keep))
            predictions[(seed,name)]=p
            results.append({'seed':seed,'method':name,'patients':len(pids),'positive_patients':int(py.sum()),
                'landmarks':len(rows),'min_fitted_features':min(counts),'max_fitted_features':max(counts),
                **metrics(y,p,w),'min_probability':float(p.min()),'max_probability':float(p.max())})
            print('Completed Bayesian development',seed,name,flush=True)
    intervals=[];pairs=[]
    old=[json.loads(s) for s in (private/'cross_validated_predictions.jsonl').read_text().splitlines()]
    index={(r['patient_id'],r['index_age_hours']):r for r in old}
    baseline=np.array([index[(r['patient_id'],r['index_age_hours'])]['snapshot_logistic'] for r in rows])
    for name in METHODS:
        p=predictions[(31,name)];interval=clustered_ci(y,p,rows)
        for metric,bounds in interval['intervals'].items():
            intervals.append({'method':name,'seed':31,'metric':metric,'lower_95':bounds[0],'upper_95':bounds[1],
                'resamples':2000,'skipped_single_class':interval['skipped_single_class'],'unit':'infant'})
        pair=clustered_ci(y,p,rows,comparison=baseline)
        for metric,bounds in pair['intervals'].items():
            pairs.append({'method':name,'comparison':'minus prior snapshot logistic','seed':31,'metric':metric,
                'lower_95':bounds[0],'upper_95':bounds[1],'resamples':2000,'skipped_single_class':pair['skipped_single_class']})
    # Fit every predeclared arm on the full development cohort, without selecting
    # a winner on held-out results or installing any candidate in the app.
    artifacts={}
    for name,(tree,cols) in METHODS.items():
        x=np.array([[f[c] for c in cols] for f in extracted],dtype=float)
        keep=[j for j in range(x.shape[1]) if len(set(groups[np.isfinite(x[:,j])]))>=5 and np.nanstd(x[:,j])>0]
        model=TemporalBayes(tree=tree).fit(x[:,keep],y,w)
        restored=TemporalBayes.from_dict(model.to_dict())
        np.testing.assert_allclose(restored.predict_proba(x[:,keep]),model.predict_proba(x[:,keep]),atol=1e-12)
        artifacts[name]={'model':model.to_dict(),'features':[cols[j] for j in keep]}
    save(private/'bayes_experiment/models.json',artifacts)
    with (private/'bayes_experiment/oof_predictions.jsonl').open('w') as f:
        for i,r in enumerate(rows):f.write(json.dumps({'patient_id':r['patient_id'],'age_hours':r['index_age_hours'],
            'label':r['label'],'predictions':{f'{seed}:{name}':float(p[i]) for (seed,name),p in predictions.items()}})+'\n')
    save(out/'results.json',{'protocol':protocol,'results':results,'intervals':intervals,'paired_intervals':pairs,
        'fold_counts':fold_counts,'clinical_ready':False,'probability_calibration':'not independently established',
        'interpretation':'Repeated patient-disjoint development on the same seven positive infants. No architecture can establish clinical reliability from these comparisons; no model is promoted.'})
    write_csv(out/'metrics.csv',results);write_csv(out/'intervals.csv',intervals);write_csv(out/'paired_intervals.csv',pairs)
    write_csv(out/'fold_counts.csv',fold_counts)
    print(json.dumps({'clinical_ready':False,'results':results},indent=2))


if __name__=='__main__':main()
