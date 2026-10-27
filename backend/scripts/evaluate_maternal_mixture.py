"""Exploratory maternal/neonatal stacking and cross-source transfer; never clinical validation."""
import argparse,hashlib,io,json,platform,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,log_loss,confusion_matrix
from sklearn.model_selection import StratifiedKFold,train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from ml.research_cohort import partitions

MATERNAL=['gestational_age_weeks','birth_weight_kg','maternal_age','prom','maternal_infection',
          'cesarean','apgar_1min','apgar_5min','resuscitation_needed']
CLINICAL=['fever','hypothermia','respiratory_distress','poor_feeding','lethargy','jaundice']
SHARED=['gestational_age_weeks','birth_weight_kg','cesarean']
FORBIDDEN={'patient_id','sepsis_status','sepsis_onset','culture_confirmed','pathogen','outcome',
           'hospital_days','sepsis_probability_score','low_birth_weight','very_low_birth_weight','young_mother'}
SEED=20261027

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def prepare(frame):
    frame=frame.copy()
    for key in ['prom','maternal_infection','resuscitation_needed',*CLINICAL]:
        values=frame[key].astype(str).str.lower()
        if not set(values.unique())<={'true','false'}:raise ValueError('Unrecognized boolean: '+key)
        frame[key]=values.eq('true').astype(float)
    if not set(frame.delivery_mode.unique())<={'Vaginal','C-section'}:raise ValueError('Unknown delivery mapping')
    frame['cesarean']=frame.delivery_mode.eq('C-section').astype(float)
    frame['target']=frame.sepsis_status.eq('Positive').astype(int)
    # Conditional case/control simulation, NOT a prospective EOS incidence cohort.
    return frame.loc[frame.sepsis_status.eq('Negative')|frame.sepsis_onset.eq('Early-onset')].copy()

def logistic():return Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler()),
    ('model',LogisticRegression(C=1,max_iter=1500,random_state=SEED))])

def clinical():return Pipeline([('impute',SimpleImputer(strategy='median')),
    ('model',RandomForestClassifier(n_estimators=120,max_depth=4,min_samples_leaf=20,n_jobs=2,random_state=SEED))])

def metrics(y,p,threshold):
    tn,fp,fn,tp=confusion_matrix(y,p>=threshold,labels=[0,1]).ravel()
    return {'n':len(y),'positive':int(np.sum(y)),'auroc':float(roc_auc_score(y,p)),
        'auprc':float(average_precision_score(y,p)),'brier':float(brier_score_loss(y,p)),
        'log_loss':float(log_loss(y,p)),'threshold':float(threshold),
        'sensitivity':float(tp/(tp+fn)),'specificity':float(tn/(tn+fp)),
        'accuracy':float((tp+tn)/len(y))}

def export(pipe,features):
    model=pipe.named_steps['model'];a={'features':features,'median':pipe.named_steps['impute'].statistics_.tolist()}
    if isinstance(model,LogisticRegression):
        scaler=pipe.named_steps['scale']
        return {**a,'kind':'logistic','mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),
            'coefficients':model.coef_[0].tolist(),'intercept':float(model.intercept_[0])}
    trees=[]
    for fitted in model.estimators_:
        t=fitted.tree_;counts=t.value[:,0,:];probs=counts[:,1]/counts.sum(axis=1)
        trees.append({'left':t.children_left.tolist(),'right':t.children_right.tolist(),
            'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),'probability':probs.tolist()})
    return {**a,'kind':'forest','trees':trees}

def portable(a,x):
    x=np.asarray(x,dtype=float);x=np.where(np.isnan(x),np.array(a['median']),x)
    if a['kind']=='logistic':
        z=((x-a['mean'])/a['scale'])@np.array(a['coefficients'])+a['intercept']
        return 1/(1+np.exp(-np.clip(z,-700,700)))
    x=x.astype(np.float32);prob=[]
    for t in a['trees']:
        left,right,feature,threshold=map(np.array,[t['left'],t['right'],t['feature'],t['threshold']])
        nodes=np.zeros(len(x),dtype=int)
        while (left[nodes]!=-1).any():
            ix=np.flatnonzero(left[nodes]!=-1);n=nodes[ix]
            nodes[ix]=np.where(x[ix,feature[n]]<=threshold[n],left[n],right[n])
        prob.append(np.array(t['probability'])[nodes])
    return np.mean(prob,axis=0)

def main():
    p=argparse.ArgumentParser();p.add_argument('--development',type=Path,required=True);p.add_argument('--test',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not (set(MATERNAL+CLINICAL+SHARED)&FORBIDDEN)
    raw_dev=pd.read_csv(a.development);raw_test=pd.read_csv(a.test)
    # IDs repeat between files. Remove development IDs appearing in the test
    # without inspecting test outcomes; never invent a shared-patient join.
    eligible_dev=raw_dev.loc[~raw_dev.patient_id.isin(raw_test.patient_id)].copy()
    dev,test=prepare(eligible_dev),prepare(raw_test)
    fit_ix,val_ix=train_test_split(np.arange(len(dev)),test_size=.2,stratify=dev.target,random_state=SEED)
    fit,val=dev.iloc[fit_ix],dev.iloc[val_ix];y=fit.target.to_numpy(int)
    protocol={'seed':SEED,'source_synthetic':True,'clinical_eos_eligible':False,
        'target':'Synthetic Early-onset sepsis label versus Negative, with Late-onset cases excluded',
        'development_rows_before_filter':len(raw_dev),'development_rows_after_id_exclusion':len(eligible_dev),
        'fit_n':len(fit),'validation_n':len(val),'file_defined_test_n':len(test),
        'fit_test_id_overlap':len(set(fit.patient_id)&set(test.patient_id)),
        'maternal_perinatal_inputs':MATERNAL,'concurrent_clinical_inputs':CLINICAL,'common_inputs':SHARED,
        'forbidden_as_predictors':sorted(FORBIDDEN),'laboratory_inputs_omitted':'Untimed WBC/CRP; no guessed unit alignment with old source.',
        'stacking':'Five-fold out-of-fold base predictions on fit only; logistic meta-model; validation-only threshold targeting 90% sensitivity.',
        'common_source_target_compatibility':'NOT ESTABLISHED: pooling is an explicitly hypothetical transfer stress test, not an approved combined cohort.',
        'source_hashes':{k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in [('development',a.development),('test',a.test),('original_archive',a.archive)]},
        'test_scope':'File-defined ID-disjoint synthetic holdout sharing source generation assumptions, not clinical external validation.'}
    save(a.output/'protocol.json',protocol)
    base_models=[logistic(),clinical()];feature_sets=[MATERNAL,CLINICAL];oof=np.zeros((len(fit),2))
    cv=StratifiedKFold(5,shuffle=True,random_state=SEED)
    for tr,ho in cv.split(fit,y):
        for j,(model,cols) in enumerate(zip(base_models,feature_sets)):
            fitted=clone(model).fit(fit.iloc[tr][cols],y[tr])
            oof[ho,j]=fitted.predict_proba(fit.iloc[ho][cols])[:,1]
    meta=logistic().fit(oof,y)
    for model,cols in zip(base_models,feature_sets):model.fit(fit[cols],y)
    val_base=np.column_stack([m.predict_proba(val[c])[:,1] for m,c in zip(base_models,feature_sets)])
    test_base=np.column_stack([m.predict_proba(test[c])[:,1] for m,c in zip(base_models,feature_sets)])
    pv=meta.predict_proba(val_base)[:,1];pt=meta.predict_proba(test_base)[:,1]
    arms={}
    for name,v,t in [('maternal_perinatal',val_base[:,0],test_base[:,0]),
                     ('neonatal_clinical',val_base[:,1],test_base[:,1]),('mixed_stacked',pv,pt)]:
        threshold=float(np.quantile(v[val.target.eq(1)],.1))
        arms[name]={'validation':metrics(val.target.to_numpy(),v,threshold),'synthetic_test':metrics(test.target.to_numpy(),t,threshold)}
    flat=logistic().fit(fit[MATERNAL+CLINICAL],y)
    fv=flat.predict_proba(val[MATERNAL+CLINICAL])[:,1];ft=flat.predict_proba(test[MATERNAL+CLINICAL])[:,1]
    threshold=float(np.quantile(fv[val.target.eq(1)],.1))
    arms['flat_combined_logistic']={'validation':metrics(val.target.to_numpy(),fv,threshold),
        'synthetic_test':metrics(test.target.to_numpy(),ft,threshold)}
    artifact={'purpose':'Synthetic simulation only; not installed in the application',
        'clinical_eos_eligible':False,'feature_contract':'synthetic-maternal-mixture-v1',
        'target':protocol['target'],'branches':[export(m,c) for m,c in zip(base_models,feature_sets)],
        'meta':export(meta,['maternal_perinatal_score','neonatal_clinical_score']),
        'threshold':arms['mixed_stacked']['validation']['threshold']}
    bp=np.column_stack([portable(part,test[cols].to_numpy()) for part,cols in zip(artifact['branches'],feature_sets)])
    np.testing.assert_allclose(portable(artifact['meta'],bp),pt,atol=1e-7)
    save(a.output/'mixed_model.json',artifact)
    # Honest cross-source experiment: no row linkage and no imputed maternal
    # attributes. Only GA, kg birth weight and mapped delivery category overlap.
    with zipfile.ZipFile(a.archive) as archive:old=pd.read_csv(io.BytesIO(archive.read('Neonatal_Sepsis.csv')))
    groups=partitions(old);old=old.loc[old.Postnatal_Age.between(0,2)].copy()
    old['gestational_age_weeks']=old.Gestational_Age;old['birth_weight_kg']=old.Birth_Weight
    if not set(old.Delivery_Mode.unique())<={'Vaginal','Cesarean'}:raise ValueError('Unknown original delivery mapping')
    old['cesarean']=old.Delivery_Mode.eq('Cesarean').astype(float);old['target']=old.Sepsis_Label.astype(int)
    ofit=old.loc[old.Patient_ID.isin(groups[0])];otest=old.loc[old.Patient_ID.isin(groups[3])]
    old_model=logistic().fit(ofit[SHARED],ofit.target);new_model=logistic().fit(fit[SHARED],fit.target)
    pool=pd.concat([ofit[SHARED+['target']],fit[SHARED+['target']]],ignore_index=True)
    weight=np.r_[np.full(len(ofit),len(pool)/(2*len(ofit))),np.full(len(fit),len(pool)/(2*len(fit)))]
    pooled=logistic().fit(pool[SHARED],pool.target,model__sample_weight=weight)
    transfer={}
    for name,m in [('original_only',old_model),('synthetic_only',new_model),('hypothetical_source_balanced_pool',pooled)]:
        transfer[name]={domain:metrics(frame.target.to_numpy(),m.predict_proba(frame[SHARED])[:,1],.5)
            for domain,frame in [('original_supplied_label_test',otest),('synthetic_early_label_test',test)]}
    save(a.output/'shared_feature_models.json',{'clinical_eos_eligible':False,'endpoint_compatibility_verified':False,
        'models':{n:export(m,SHARED) for n,m in [('original_only',old_model),('synthetic_only',new_model),('hypothetical_source_balanced_pool',pooled)]}})
    rng=np.random.default_rng(SEED);boot=[]
    yt=test.target.to_numpy(int)
    for _ in range(500):
        ix=rng.integers(0,len(yt),len(yt))
        if len(np.unique(yt[ix]))==2:boot.append(roc_auc_score(yt[ix],pt[ix]))
    controls=[]
    for seed in [31,47,83]:
        perm=np.random.default_rng(seed).permutation(y)
        control=logistic().fit(fit[MATERNAL+CLINICAL],perm).predict_proba(test[MATERNAL+CLINICAL])[:,1]
        controls.append({'seed':seed,'test_auroc_original_labels':float(roc_auc_score(yt,control))})
    symptom_counts=test[CLINICAL].sum(axis=1)
    generated_sign_diagnostic={'post_hoc':True,'not_a_clinical_rule':True,
        'test_symptom_count_auroc':float(roc_auc_score(yt,symptom_counts)),
        'test_count_ranges_by_label':{str(label):{'min':float(symptom_counts[test.target.eq(label)].min()),
            'max':float(symptom_counts[test.target.eq(label)].max())} for label in [0,1]}}
    report={'protocol':protocol,'models':arms,'mixed_test_auroc_bootstrap_95':np.quantile(boot,[.025,.975]).tolist(),
        'bootstrap_repeats':500,'shared_feature_transfer_stress_test':transfer,'training_label_shuffle_controls':controls,
        'generated_clinical_sign_diagnostic':generated_sign_diagnostic,
        'portable_prediction_parity_atol':1e-7,'packages':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__},
        'interpretation':['Maternal and neonatal branches are combined only on the same synthetic individuals using out-of-fold predictions.',
            'No old patient was joined to a synthetic patient; no maternal facts were invented or imputed across sources.',
            'Three-feature pooling assumes outcome compatibility that has not been established; it is a feasibility stress test only.',
            'Synthetic clinical signs may reflect label-conditional generation. High discrimination can reproduce generator rules.',
            'Excluded late-onset positives and unknown ages in negatives prevent estimation of prospective EOS incidence.',
            'This experiment neither validates nor replaces the application model; a time-aware adjudicated cohort is required.']}
    save(a.output/'results.json',report)
    save(a.output/'manifest.json',{'clinical_eos_eligible':False,
        'experiment_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'artifacts':{name:hashlib.sha256((a.output/name).read_bytes()).hexdigest()
            for name in ['protocol.json','results.json','mixed_model.json','shared_feature_models.json']}})
    print(json.dumps({'models':arms,'mixed_auc_95':report['mixed_test_auroc_bootstrap_95'],'transfer':transfer,'clinical_use':False}))

if __name__=='__main__':main()
