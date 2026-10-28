"""Paper-inspired Boruta/RF comparison, not reproduction or external validation.

Restricted records and fitted estimators remain under ignored data/. Original
R code is inspected, never executed. Feature/threshold selection never sees the
corresponding test patients. This is further development on exposed cohorts.
"""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'tmp/bmj-model-deps')]
from boruta import BorutaPy
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score,average_precision_score,confusion_matrix,brier_score_loss
from ml.pic_dataset import save,digest
from ml.dynamic_features import features
from ml.improve_pic_models import COMPACT
from ml.research_cohort import partitions
import pandas as pd
import joblib
from zipfile import ZipFile
OUT=ROOT/'output/research/bmj_boruta_adaptation';PRIVATE=ROOT/'data/bmj_boruta_adaptation'
ARMS=['all_features_rf','balanced_rf','boruta_balanced_rf']


def weights(g):
    u,n=np.unique(g,return_counts=True);lookup=dict(zip(u,n));return np.array([1/lookup[i] for i in g])


def threshold_90(y,p,w):
    # Select only from an independent threshold set. Include zero explicitly:
    # a 90% sensitivity target may degenerate to an all-positive classifier.
    options=np.unique(np.r_[0.,p]);best=None
    for t in options:
        tn,fp,fn,tp=confusion_matrix(y,p>=t,labels=[0,1],sample_weight=w).ravel()
        sens=tp/(tp+fn);spec=tn/(tn+fp)
        if sens>=.9 and (best is None or (spec,t)>(best[0],best[1])):best=(spec,float(t))
    return best[1]


def measure(y,p,d,w):
    tn,fp,fn,tp=confusion_matrix(y,d,labels=[0,1],sample_weight=w).ravel()
    return {'auroc':float(roc_auc_score(y,p,sample_weight=w)),'auprc':float(average_precision_score(y,p,sample_weight=w)),
        'accuracy':float((tp+tn)/(tp+tn+fp+fn)),'sensitivity':float(tp/(tp+fn)),
        'specificity':float(tn/(tn+fp)),'precision':float(tp/(tp+fp)) if tp+fp else None,
        'brier':float(brier_score_loss(y,p,sample_weight=w)),'predicted_positive_weight_fraction':float(np.average(d,weights=w))}


def build_selector(x,y,g,age,seed):
    # One latest training observation per infant prevents repeated landmarks
    # from becoming independent significance evidence in Boruta.
    ix=np.array([max(np.flatnonzero(g==i),key=lambda j:age[j]) for i in sorted(set(g))])
    keep=[j for j in range(x.shape[1]) if np.isfinite(x[ix,j]).sum()>=5 and np.nanstd(x[ix,j])>0]
    raw=x[:,keep];med=np.nanmedian(raw[ix],axis=0);filled=np.where(np.isnan(raw),med,raw)
    rf=RandomForestClassifier(n_estimators=1000,max_depth=5,class_weight='balanced',n_jobs=2,random_state=seed)
    selector=BorutaPy(rf,n_estimators=1000,max_iter=30,perc=100,alpha=.05,two_step=True,random_state=seed)
    selector.fit(filled[ix],y[ix]);chosen=np.flatnonzero(selector.support_)
    importance=np.nanmean(selector.importance_history_[1:],axis=0)
    order=sorted(chosen,key=lambda j:(-importance[j],j));retained=[]
    for j in order:
        if all(abs(np.corrcoef(filled[ix,j],filled[ix,k])[0,1])<=.7 for k in retained):retained.append(j)
    return {'variable_columns':keep,'median':med.tolist(),'confirmed':[keep[j] for j in chosen],
        'tentative':[keep[j] for j in np.flatnonzero(selector.support_weak_)],
        'selected':[keep[j] for j in retained],'selector_infants':len(ix),
        'positive_selector_infants':int(y[ix].sum()),'boruta_iterations':len(selector.importance_history_)-1,
        'selector_status':'confirmed_features' if retained else 'no_confirmed_features_prevalence_fallback'}


def balanced_weights(y,g):
    # Kaggle labels can change within a patient ID, so a patient cannot be
    # assigned one invented outcome for whole-patient oversampling. Balance
    # observed classes using their training-only, infant-normalized mass.
    w=weights(g);total=w.sum()
    for label in [0,1]:
        mask=y==label
        if not mask.any():raise ValueError('Both training classes required')
        w[mask]*=total/(2*w[mask].sum())
    return w


def main():
    OUT.mkdir(parents=True,exist_ok=True);PRIVATE.mkdir(parents=True,exist_ok=True)
    archive=Path('C:/Users/hadia/Downloads/archive (1).zip');picpath=ROOT/'data/picdb_private/landmarks.jsonl'
    protocol={'stage':'paper-inspired exposed-cohort development','paper':'https://doi.org/10.1136/bmjpo-2025-003561',
        'exact_replication':False,'adaptations':['scikit-learn/BorutaPy, not R/H2O','1000 selection trees per paper prose; 30-iteration compute cap, not repository ntree=10000/maxRuns=2000',
        'BorutaPy Gini-based importance and one latest training row per infant','class-balanced infant-normalized loss weights, not ROSE oversampling; no synthetic training cases',
        'missing original maternal/clinical/centre/lagged exposure variables not fabricated','strict patient-disjoint feature/threshold/test sets'],
        'selection_seed':31,'forest_seeds':[31,47,83],'forest':{'trees':120,'max_depth':8,'mtries':5,'min_samples_leaf':1},
        'correlation_prune':'.7 absolute Pearson on selector-training infants; retain higher training Boruta importance',
        'threshold':'highest specificity reaching >=90% patient-weighted sensitivity on independent threshold patients; not test',
        'arms':ARMS,'kaggle_split':'Original patient-disjoint 55/15/15/15 partition seed31; fit=55%, threshold=validation15%, original calibration15% unused, test15%',
        'pic_split':'Original seed31 patient-stratified three outer folds; within training fold reserve 25% per-class infants for threshold selection (at least one positive)',
        'probabilities':'No independent clinical calibration; oversampling scores are not EOS probabilities',
        'bootstrap':{'unit':'infant','resamples':2000,'seed':31},
        'sources':{'kaggle_archive_sha256':digest(archive),'pic_cohort_sha256':digest(picpath)},
        'code_sha256':digest(Path(__file__)),'boruta_version':'0.4.3','clinical_ready':False}
    proto=OUT/'protocol.json'
    if proto.exists() and json.loads(proto.read_text())!=protocol:raise ValueError('Protocol drift')
    save(proto,protocol)
    with ZipFile(archive) as z:k=pd.read_csv(z.open('Neonatal_Sepsis.csv'))
    k=k.loc[k.Postnatal_Age.between(0,2)].copy()
    raw=['Gestational_Age','Birth_Weight','Postnatal_Age','Apgar','HR','Resp','Temp','SpO2','BP','Oxygen','WBC','CRP','PCT','Platelets','Lactate','Hemoglobin']
    kx=k[raw].astype(float).to_numpy();kx=np.c_[kx,(k.Sex=='Female').astype(float),(k.Delivery_Mode=='Cesarean').astype(float)]
    kg=k.Patient_ID.astype(str).to_numpy();ky=k.Sepsis_Label.to_numpy();ka=k.Observation_Hour.to_numpy()
    # Recreate the exact previous partitions on all source patient IDs, then
    # restrict to the already declared early-age research subset.
    with ZipFile(archive) as z:allk=pd.read_csv(z.open('Neonatal_Sepsis.csv'),usecols=['Patient_ID'])
    parts=partitions(allk);ks=[(np.flatnonzero(np.isin(k.Patient_ID,list(parts[0]))),np.flatnonzero(np.isin(k.Patient_ID,list(parts[2]))),np.flatnonzero(np.isin(k.Patient_ID,list(parts[3]))))]
    pr=[json.loads(s) for s in picpath.read_text().splitlines()];pf=[features(r['index_age_hours'],r['sex'],r['events']) for r in pr]
    px=np.array([[v[c] for c in COMPACT] for v in pf],dtype=float);pg=np.array([r['patient_id'] for r in pr]);py=np.array([r['label'] for r in pr]);pa=np.array([r['index_age_hours'] for r in pr])
    ids=np.array(sorted(set(pg)));iy=np.array([py[np.flatnonzero(pg==i)[0]] for i in ids]);ps=[]
    for fold,(tr,te) in enumerate(StratifiedKFold(3,shuffle=True,random_state=31).split(ids,iy)):
        rng=np.random.default_rng(131+fold);reserve=[]
        for lab in [0,1]:
            eligible=ids[tr][iy[tr]==lab];reserve.extend(rng.choice(eligible,max(1,int(len(eligible)*.25)),replace=False).tolist())
        threshold_ids=set(reserve);fit_ids=set(ids[tr])-threshold_ids
        ps.append((np.flatnonzero(np.isin(pg,list(fit_ids))),np.flatnonzero(np.isin(pg,reserve)),np.flatnonzero(np.isin(pg,ids[te]))))
    metrics=[];feature_rows=[];split_rows=[];allpred={}
    for dataset,x,y,g,age,names,splits in [('kaggle',kx,ky,kg,ka,raw+['sex_female','delivery_cesarean'],ks),('pic',px,py,pg,pa,list(COMPACT),ps)]:
        (PRIVATE/dataset).mkdir(parents=True,exist_ok=True)
        predictions={(arm,seed):{'p':np.zeros(len(y)),'d':np.zeros(len(y),dtype=bool),'valid':np.zeros(len(y),dtype=bool)} for arm in ARMS for seed in [31,47,83]}
        for fold,(tr,cal,te) in enumerate(splits):
            assert not set(g[tr])&set(g[cal]) and not set(g[tr])&set(g[te]) and not set(g[cal])&set(g[te])
            target=PRIVATE/dataset/f'fold{fold}.json'
            if target.exists():
                cached=json.loads(target.read_text());assert cached['protocol_sha256']==digest(proto)
            else:
                selector=build_selector(x[tr],y[tr],g[tr],age[tr],31)
                cached={'protocol_sha256':digest(proto),'selector':selector,'fits':[]}
                for arm in ARMS:
                    cols=selector['selected'] if arm=='boruta_balanced_rf' else selector['variable_columns']
                    median=np.nanmedian(x[tr][:,cols],axis=0) if cols else np.array([])
                    def matrix(ix):return np.where(np.isnan(x[ix][:,cols]),median,x[ix][:,cols])
                    for seed in [31,47,83]:
                        fallback=not cols;model=None
                        if fallback:
                            prior=float(np.average(y[tr],weights=weights(g[tr])));cp=np.full(len(cal),prior);tp=np.full(len(te),prior)
                        else:
                            train_x=matrix(tr);train_y=y[tr];tw=weights(g[tr])
                            if arm!='all_features_rf':
                                tw=balanced_weights(train_y,g[tr])
                            model=RandomForestClassifier(n_estimators=120,max_depth=8,max_features=min(5,len(cols)),min_samples_leaf=1,n_jobs=2,random_state=seed).fit(train_x,train_y,sample_weight=tw)
                            cp=model.predict_proba(matrix(cal))[:,1];tp=model.predict_proba(matrix(te))[:,1]
                        cut=threshold_90(y[cal],cp,weights(g[cal]));cm=measure(y[cal],cp,cp>=cut,weights(g[cal]))
                        cached['fits'].append({'arm':arm,'seed':seed,'p':tp.tolist(),'d':(tp>=cut).tolist(),'threshold':cut,'threshold_set_sensitivity':cm['sensitivity'],'threshold_set_specificity':cm['specificity'],'prevalence_fallback':fallback})
                        if model is not None and seed==31:joblib.dump({'model':model,'columns':cols,'features':[names[j] for j in cols],'median':median,'threshold':cut},PRIVATE/dataset/f'fold{fold}_{arm}.joblib')
                save(target,cached)
                print('Saved',dataset,'fold',fold,'confirmed',len(selector['confirmed']),'retained',len(selector['selected']),flush=True)
            s=cached['selector'];feature_rows.append({'dataset':dataset,'fold':fold,**s,'selected_names':[names[j] for j in s['selected']]})
            split_rows.append({'dataset':dataset,'fold':fold,'fit_infants':len(set(g[tr])),'fit_positive_infants':len(set(g[tr][y[tr]==1])),
                'threshold_infants':len(set(g[cal])),'threshold_positive_infants':len(set(g[cal][y[cal]==1])),
                'test_infants':len(set(g[te])),'test_positive_infants':len(set(g[te][y[te]==1])),'patient_overlap':0})
            for fit in cached['fits']:
                v=predictions[(fit['arm'],fit['seed'])];v['p'][te]=fit['p'];v['d'][te]=fit['d'];v['valid'][te]=True
        for (arm,seed),v in predictions.items():
            mask=v['valid'];m=measure(y[mask],v['p'][mask],v['d'][mask],weights(g[mask]));metrics.append({'dataset':dataset,'arm':arm,'seed':seed,'scored_rows':int(mask.sum()),'scored_infants':len(set(g[mask])),**m})
        mask=predictions[(ARMS[0],31)]['valid'];allpred[dataset]={'y':y[mask],'g':g[mask],'pred':{f'{arm}:{seed}':{'p':v['p'][mask],'d':v['d'][mask]} for (arm,seed),v in predictions.items()}}
        save(OUT/'metrics.json',metrics);save(OUT/'features.json',feature_rows);save(OUT/'splits.json',split_rows)
    intervals=[];paired=[]
    for dataset,entry in allpred.items():
        y,g=entry['y'],entry['g'];w=weights(g);groups=[np.flatnonzero(g==i) for i in sorted(set(g))];rng=np.random.default_rng(31)
        dist={a:[] for a in ARMS};delta=[];skipped=0
        for _ in range(2000):
            ix=np.concatenate([groups[i] for i in rng.integers(0,len(groups),len(groups))])
            if len(set(y[ix]))<2:skipped+=1;continue
            estimates={}
            for arm in ARMS:
                p=entry['pred'][f'{arm}:31'];m=measure(y[ix],p['p'][ix],p['d'][ix],w[ix]);dist[arm].append(m);estimates[arm]=m
            delta.append(estimates['boruta_balanced_rf']['auroc']-estimates['balanced_rf']['auroc'])
        for arm,values in dist.items():
            for metric in values[0]:
                vals=[v[metric] for v in values if v[metric] is not None];lo,hi=np.quantile(vals,[.025,.975]) if vals else (None,None)
                intervals.append({'dataset':dataset,'arm':arm,'metric':metric,'low_95':lo,'high_95':hi,'repeats':2000,'skipped_single_class':skipped})
        lo,hi=np.quantile(delta,[.025,.975]);paired.append({'dataset':dataset,'contrast':'Boruta balanced RF minus all-feature balanced RF AUROC','low_95':lo,'high_95':hi})
    save(OUT/'results.json',{'protocol':protocol,'metrics':metrics,'features':feature_rows,'splits':split_rows,'intervals':intervals,'paired':paired,'clinical_ready':False,'app_model_changed':False})
    print('Paper-inspired comparison complete; no model promoted.',flush=True)


if __name__=='__main__':main()
