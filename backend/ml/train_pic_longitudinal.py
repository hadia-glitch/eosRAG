"""Patient-disjoint, local-only longitudinal model development on actual PIC data.

Candidate comparison is cross-validation development, not external validation.
No synthetic maternal rows are joined to real infants. No model is auto-deployed.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,sys,importlib.metadata
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,confusion_matrix
from sklearn.model_selection import StratifiedKFold

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from ml.dynamic_features import GROUPS,features
from ml.pic_dataset import VERSION,save,digest
from ml.train import export_estimator

SEED=31
METHODS={'snapshot_logistic':('snapshot','logistic'), 'trend_logistic':('trend','logistic'),
         'binned_logistic':('binned','logistic'),'trend_forest':('trend','forest')}


def weighting(records):
    unique,counts=np.unique([r['patient_id'] for r in records],return_counts=True)
    lookup=dict(zip(unique,counts))
    return np.array([1/lookup[r['patient_id']] for r in records])


def preprocess(x,columns):
    keep=[i for i in range(x.shape[1]) if np.isfinite(x[:,i]).sum()>=5 and np.nanstd(x[:,i])>0]
    if not keep:raise ValueError('No variable, observed training predictors')
    raw=x[:,keep];med=np.nanmedian(raw,axis=0);filled=np.where(np.isnan(raw),med,raw)
    mean=filled.mean(0);scale=filled.std(0);scale[scale==0]=1
    return {'indices':keep,'features':[columns[i] for i in keep],'median':med.tolist(),'mean':mean.tolist(),'scale':scale.tolist()}


def transform(x,prep):
    raw=x[:,prep['indices']];filled=np.where(np.isnan(raw),prep['median'],raw)
    return np.c_[(filled-prep['mean'])/prep['scale'],np.isnan(raw).astype(float)]


def estimator(kind):
    if kind=='logistic':return LogisticRegression(C=.03,max_iter=2000,random_state=SEED)
    return RandomForestClassifier(n_estimators=160,max_depth=3,min_samples_leaf=20,
                                  max_features=.6,n_jobs=2,random_state=SEED)


def metrics(y,p,w):
    return {'auroc':float(roc_auc_score(y,p,sample_weight=w)),
            'auprc':float(average_precision_score(y,p,sample_weight=w)),
            'brier':float(brier_score_loss(y,p,sample_weight=w)),
            'mean_probability':float(np.average(p,weights=w)),
            'observed_rate':float(np.average(y,weights=w))}


def clustered_ci(y,p,records,comparison=None,repeats=2000):
    # Bootstrap independent infants, preserving every landmark in a draw.
    w=weighting(records);groups={}
    for i,r in enumerate(records):groups.setdefault(r['patient_id'],[]).append(i)
    groups=[np.array(v) for v in groups.values()];rng=np.random.default_rng(SEED)
    distributions={m:[] for m in ['auroc','auprc','brier']};skipped=0
    for _ in range(repeats):
        ix=np.concatenate([groups[i] for i in rng.integers(0,len(groups),len(groups))])
        if len(np.unique(y[ix]))!=2:skipped+=1;continue
        a=metrics(y[ix],p[ix],w[ix]);b=metrics(y[ix],comparison[ix],w[ix]) if comparison is not None else {}
        for m in distributions:distributions[m].append(a[m]-b.get(m,0))
    return {'repeats':repeats,'skipped_single_class':skipped,'seed':SEED,'unit':'patient',
            'intervals':{m:np.quantile(v,[.025,.975]).tolist() for m,v in distributions.items()}}


def write_csv(path,rows):
    if not rows:return
    with path.open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def portable(artifact,x):
    from ml.research_cohort import portable_probability
    # That shared portable evaluator accepts already transformed predictors.
    return portable_probability(artifact,transform(x,artifact['preprocessing']))


def main(cohort,output,private):
    if not private.resolve().is_relative_to((ROOT/'data').resolve()):
        raise ValueError('Patient-level predictions and real-data weights must remain in ignored data/')
    records=[json.loads(line) for line in cohort.read_text().splitlines() if line.strip()]
    labels={r['patient_id']:r['label'] for r in records}
    for r in records:
        if r['label']!=labels[r['patient_id']] or r['index_age_hours']>=r['first_culture_age_hours']:
            raise ValueError('Outcome or prediagnostic landmark inconsistency')
        if any(max(e['age_hours'],e['available_age_hours'])>r['index_age_hours'] for e in r['events']):
            raise ValueError('Future predictor leak')
    patients=np.array(sorted(labels));py=np.array([labels[i] for i in patients])
    if min(np.bincount(py,minlength=2))<3:raise ValueError('Too few independent events even for exploratory three-fold comparison')
    output.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True,exist_ok=True)
    protocol={'stage':'development_only','clinical_eos_eligible':False,'feature_version':VERSION,'seed':SEED,
        'cohort_sha256':digest(cohort),'cohort_protocol_sha256':digest(output/'protocol.json'),
        'models':METHODS,'folds':3,'split':'Patient-stratified random folds; dates are shifted, not calendar-temporal validation',
        'preprocessing':'Training-fold-only variable column selection, median imputation, standard scaling, explicit missingness indicators. No outcome or synthetic donor imputation.',
        'logistic_C':.03,'forest':{'n_estimators':160,'max_depth':3,'min_samples_leaf':20,'max_features':.6},
        'weights':'Equal total weight per patient despite repeated landmarks',
        'thresholds':[.01,.02,.05,.10],'threshold_use':'Descriptive research operating points only; no clinical action threshold',
        'selection':'Highest patient-weighted cross-validated AUPRC among longitudinal candidates for the dynamic research artifact; the snapshot baseline is retained and may be higher. Selection on these folds is development, not independent validation.',
        'neural_minimum_positive_patients':100,'neural_policy':'Do not fit an underdetermined recurrent network below this engineering floor; not a clinical sample-size justification.',
        'calibration':'No separate calibration cohort is available. Probabilities are research model scores, not validated absolute EOS risks.',
        'bootstrap':{'unit':'patient','repeats':2000,'seed':SEED},
        'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'backend/ml/dynamic_features.py',ROOT/'backend/ml/dynamic_contract.py',ROOT/'backend/ml/pic_dataset.py']},
        'packages':{p:importlib.metadata.version(p) for p in ['numpy','scikit-learn','pandas','pydantic']}}
    save(output/'training_protocol.json',protocol)
    extracted=[features(r['index_age_hours'],r['sex'],r['events']) for r in records]
    matrices={g:np.array([[f[c] for c in cols] for f in extracted],dtype=float) for g,cols in GROUPS.items()}
    y=np.array([r['label'] for r in records]);weights=weighting(records)
    splitter=StratifiedKFold(3,shuffle=True,random_state=SEED)
    folds=[];fold_by_patient={}
    for fold,(tr,ho) in enumerate(splitter.split(patients,py)):
        train=set(patients[tr]);test=set(patients[ho]);assert not train&test
        for p in test:fold_by_patient[p]=fold
        folds.append((np.array([i for i,r in enumerate(records) if r['patient_id'] in train]),
                      np.array([i for i,r in enumerate(records) if r['patient_id'] in test])))
    save(private/'patient_folds.json',fold_by_patient)
    oof={name:np.zeros(len(records)) for name in [*METHODS,'training_prevalence','age_only','missingness_only']}
    train_metrics={name:[] for name in METHODS};counts=[]
    for fold,(tr,ho) in enumerate(folds):
        tr_records=[records[i] for i in tr];tw=weighting(tr_records)
        counts.append({'fold':fold,'train_patients':len({records[i]['patient_id'] for i in tr}),
            'heldout_patients':len({records[i]['patient_id'] for i in ho}),
            'train_positive_patients':len({records[i]['patient_id'] for i in tr if y[i]}),
            'heldout_positive_patients':len({records[i]['patient_id'] for i in ho if y[i]})})
        oof['training_prevalence'][ho]=np.average(y[tr],weights=tw)
        for name,(group,kind) in METHODS.items():
            x=matrices[group];prep=preprocess(x[tr],GROUPS[group]);xt=transform(x[tr],prep);xh=transform(x[ho],prep)
            model=estimator(kind).fit(xt,y[tr],sample_weight=tw)
            oof[name][ho]=model.predict_proba(xh)[:,1]
            train_metrics[name].append(metrics(y[tr],model.predict_proba(xt)[:,1],tw))
        for name,x in [('age_only',matrices['snapshot'][:,:1]),('missingness_only',np.isnan(matrices['trend']).astype(float))]:
            prep=preprocess(x[tr],list(range(x.shape[1])))
            model=estimator('logistic').fit(transform(x[tr],prep),y[tr],sample_weight=tw)
            oof[name][ho]=model.predict_proba(transform(x[ho],prep))[:,1]
        print('Completed patient-disjoint fold',fold+1,'/3',flush=True)
    # Prespecified equal-vote ensemble, no learned stack on the held-out labels.
    oof['longitudinal_mean_ensemble']=np.mean([oof[n] for n in METHODS if n!='snapshot_logistic'],axis=0)
    measures={};table=[];operating=[];paired={}
    for name,p in oof.items():
        m=metrics(y,p,weights);ci=clustered_ci(y,p,records)
        measures[name]={'metrics':m,'bootstrap':ci,'training_fold_mean':
            {k:float(np.mean([r[k] for r in train_metrics[name]])) for k in m} if name in train_metrics else None}
        table.append({'method':name,'patients':len(patients),'positive_patients':int(py.sum()),'landmarks':len(records),**m,
            **{f'{k}_95_low':v[0] for k,v in ci['intervals'].items()},**{f'{k}_95_high':v[1] for k,v in ci['intervals'].items()}})
        for cut in protocol['thresholds']:
            tn,fp,fn,tp=confusion_matrix(y,p>=cut,labels=[0,1],sample_weight=weights).ravel()
            operating.append({'method':name,'threshold':cut,'sensitivity':float(tp/(tp+fn)),
                'specificity':float(tn/(tn+fp)),'ppv':float(tp/(tp+fp)) if tp+fp else None,
                'note':'Patient-weighted repeated-landmark descriptive operating point; no treatment threshold'})
        if name in METHODS and name!='snapshot_logistic' or name=='longitudinal_mean_ensemble':
            paired[name]=clustered_ci(y,p,records,comparison=oof['snapshot_logistic'])
        print('Saved metric estimates for',name,flush=True)
    # Group-level training-label shuffle controls, never shuffle landmarks
    # separately. Refit the same trend learner on exactly the same folds.
    controls=[]
    for seed in [31,47,83]:
        mapping=dict(zip(patients,np.random.default_rng(seed).permutation(py)));shuffled=np.array([mapping[r['patient_id']] for r in records]);pred=np.zeros(len(y))
        for tr,ho in folds:
            x=matrices['trend'];prep=preprocess(x[tr],GROUPS['trend'])
            model=estimator('logistic').fit(transform(x[tr],prep),shuffled[tr],sample_weight=weighting([records[i] for i in tr]))
            pred[ho]=model.predict_proba(transform(x[ho],prep))[:,1]
        controls.append({'seed':seed,'evaluation':'Original unshuffled outcomes; fixed patient folds',**metrics(y,pred,weights)})
    candidates=[n for n in METHODS if n!='snapshot_logistic']
    selected=max(candidates,key=lambda n:measures[n]['metrics']['auprc'])
    group,kind=METHODS[selected];x=matrices[group];prep=preprocess(x,GROUPS[group]);xt=transform(x,prep)
    fitted=estimator(kind).fit(xt,y,sample_weight=weights)
    artifact={'feature_version':VERSION,'model_version':selected+'-pic-seed31','kind':kind,
        'group':group,'clinical_eos_eligible':False,'validation_status':'research_only',
        'target':json.loads((output/'protocol.json').read_text())['target'],
        'preprocessing':prep,'calibration':{'slope':1.,'intercept':0.,'status':'not_independently_calibrated'},
        'training_patients':len(patients),'positive_training_patients':int(py.sum()),
        'source_cohort_sha256':digest(cohort),**export_estimator(fitted,kind)}
    np.testing.assert_allclose(portable(artifact,x),fitted.predict_proba(xt)[:,1],atol=1e-7)
    save(private/'dynamic_model.json',artifact)
    save(private/'dynamic_manifest.json',{'feature_version':VERSION,'artifact_sha256':digest(private/'dynamic_model.json'),
        'training_protocol_sha256':digest(output/'training_protocol.json'),'clinical_eos_eligible':False,
        'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'backend/ml/dynamic_features.py',ROOT/'backend/ml/dynamic_contract.py']}})
    # Individual predictions stay private under the data-use agreement.
    with (private/'cross_validated_predictions.jsonl').open('w') as f:
        for j,r in enumerate(records):f.write(json.dumps({'patient_id':r['patient_id'],'index_age_hours':r['index_age_hours'],
            'label':r['label'],'fold':fold_by_patient[r['patient_id']],**{n:float(p[j]) for n,p in oof.items()}})+'\n')
    sensitivity={}
    mask=np.array([not r['birth_time_midnight'] for r in records])
    if len(np.unique(y[mask]))==2:
        subset=[r for r,m in zip(records,mask) if m]
        sensitivity={'analysis':'Excludes midnight DOBs, using existing out-of-fold predictions; not a retrained independent study',
            'patients':len({r['patient_id'] for r in subset}),'positive_patients':len({r['patient_id'] for r in subset if r['label']}),
            'models':{n:metrics(y[mask],p[mask],weighting(subset)) for n,p in oof.items()}}
    report={'protocol':protocol,'patients':len(patients),'positive_patients':int(py.sum()),'landmarks':len(records),
        'fold_counts':counts,'comparison':measures,'paired_vs_snapshot':paired,'training_label_shuffle_controls':controls,
        'midnight_birth_time_sensitivity':sensitivity,'selected_development_model':selected,
        'selection_has_independent_test':False,'neural_model_status':'not fitted: independent positive infants below predeclared engineering floor',
        'artifact_sha256':digest(private/'dynamic_model.json'),'portable_prediction_parity_atol':1e-7,
        'clinical_ready':False,'limitations':['Very few independent positive infants; intervals do not capture phenotype uncertainty or between-site transport.',
            'Candidate selection and comparison use the same development folds. No untouched test, no external site.',
            'Raw probabilities are not independently calibrated, and the endpoint is not adjudicated EOS.',
            'Synthetic maternal factors are evaluated separately; no real infant is assigned synthetic obstetric history.',
            'Threshold operating points cannot authorize treatment, stopping or reassurance.']}
    save(output/'model_comparison.json',report)
    write_csv(output/'model_comparison.csv',table);write_csv(output/'operating_points.csv',operating)
    lines=['# PIC longitudinal development comparison','',f'{len(patients)} infants, {int(py.sum())} independent positive infants, {len(records)} pre-culture landmarks. Three patient-disjoint folds; no independent final test.','',
        '|Method|AUROC|AUPRC|Brier|','|---|---:|---:|---:|']
    for row in table:lines.append(f'|{row["method"]}|{row["auroc"]:.4f}|{row["auprc"]:.4f}|{row["brier"]:.4f}|')
    lines+=['',f'Selected for development by cross-validated AUPRC: {selected}. The artifact is local-only and not clinically approved.',
        'Patient-bootstrap 95% intervals (2,000 resamples), paired history comparisons and descriptive operating points are in the CSV/JSON outputs. Negative outcomes are preserved.',
        'The outcome is a documented named bacterial pathogen in a blood culture collected before 72 hours, not adjudicated clinical EOS. Maternal predictors are unavailable in this real cohort. No synthetic maternal history is joined to these infants.',
        'A recurrent neural model is not fitted because independent infection events are below the prespecified engineering floor. A more complex model is not justified by more rows from the same few infants.']
    (output/'results.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'selected':selected,'clinical_ready':False,'models':{k:v['metrics'] for k,v in measures.items()}},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cohort',type=Path,default=ROOT/'data/picdb_private/landmarks.jsonl')
    p.add_argument('--output',type=Path,default=ROOT/'output/research/pic_longitudinal')
    p.add_argument('--private',type=Path,default=ROOT/'data/picdb_private')
    a=p.parse_args();main(a.cohort,a.output,a.private)
