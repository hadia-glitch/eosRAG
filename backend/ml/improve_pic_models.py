"""Nested, patient-grouped PIC model selection; all restricted rows stay local.

This is further development on an exposed cohort, not external validation.
No outcome/timing definition or source record is altered to improve a score.
"""
import hashlib,importlib.metadata,json,sys
from pathlib import Path
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier,RandomForestClassifier,HistGradientBoostingClassifier
from sklearn.impute import KNNImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from ml.dynamic_features import features,GROUPS
from ml.train_pic_longitudinal import weighting,metrics,clustered_ci,write_csv
from ml.pic_dataset import save,digest

COMPACT=GROUPS['snapshot']+tuple(f'{v}__{s}' for v in ['neonatal_temperature','heart_rate','respiratory_rate','spo2'] for s in ['delta','slope_per_hour','count','recency_hours'])
CANDIDATES={
 'compact_lr_median_C001':('compact','median','lr',.01),
 'compact_lr_median_C01':('compact','median','lr',.1),
 'compact_lr_knn_C01':('compact','knn','lr',.1),
 'trend_lr_median_C003':('trend','median','lr',.03),
 'compact_forest':('compact','median','forest',None),
 'compact_balanced_forest':('compact','median','balanced_forest',None),
 'compact_extra_trees':('compact','median','extra',None),
 'compact_native_missing_boost':('compact','native','boost',None),
}


class FoldModel:
    def __init__(self,spec,seed):self.spec,self.seed=spec,seed
    def fit(self,x,y,groups,weights):
        _,imputation,kind,param=self.spec
        # Minimum distinct infants, not repeated measurements of one donor.
        self.keep=[j for j in range(x.shape[1]) if len(set(groups[np.isfinite(x[:,j])]))>=5 and np.nanstd(x[:,j])>0]
        if not self.keep:raise ValueError('No sufficiently observed training predictor')
        raw=x[:,self.keep];self.median=np.nanmedian(raw,axis=0)
        filled=np.where(np.isnan(raw),self.median,raw)
        self.mean=np.average(filled,axis=0,weights=weights)
        self.scale=np.sqrt(np.average((filled-self.mean)**2,axis=0,weights=weights));self.scale[self.scale==0]=1
        standardized=(raw-self.mean)/self.scale
        self.imputer=KNNImputer(n_neighbors=5,weights='distance').fit(standardized) if imputation=='knn' else None
        if kind=='lr':self.model=LogisticRegression(C=param,max_iter=3000,random_state=self.seed)
        elif kind in ['forest','balanced_forest','extra']:
            cls=ExtraTreesClassifier if kind=='extra' else RandomForestClassifier
            self.model=cls(n_estimators=120,max_depth=3,min_samples_leaf=20,max_features=.6,n_jobs=2,
                class_weight='balanced' if kind=='balanced_forest' else None,random_state=self.seed)
        else:self.model=HistGradientBoostingClassifier(max_iter=40,max_leaf_nodes=3,max_depth=2,
                min_samples_leaf=20,l2_regularization=10,learning_rate=.05,early_stopping=False,random_state=self.seed)
        # Preserve equal total weight per infant; unit mean matters to boost's
        # Hessian regularization and is explicit for that candidate only.
        w=weights/weights.mean() if kind=='boost' else weights
        self.model.fit(self.transform(x),y,sample_weight=w)
        return self
    def transform(self,x):
        raw=x[:,self.keep];scaled=(raw-self.mean)/self.scale
        if self.spec[1]=='knn':values=self.imputer.transform(scaled)
        elif self.spec[1]=='native':values=scaled
        else:values=np.where(np.isnan(scaled),(self.median-self.mean)/self.scale,scaled)
        return np.c_[values,np.isnan(raw).astype(float)]
    def predict(self,x):return self.model.predict_proba(self.transform(x))[:,1]


def folds(rows,seed,n=3):
    labels={r['patient_id']:r['label'] for r in rows};p=np.array(sorted(labels));y=np.array([labels[i] for i in p])
    if min(np.bincount(y,minlength=2))<n:raise ValueError('Too few independent outcomes for declared folds')
    g=np.array([r['patient_id'] for r in rows]);result=[]
    for train,test in StratifiedKFold(n,shuffle=True,random_state=seed).split(p,y):
        a=np.flatnonzero(np.isin(g,p[train]));b=np.flatnonzero(np.isin(g,p[test]))
        assert not set(g[a])&set(g[b]);result.append((a,b))
    return result


def main():
    private=ROOT/'data/picdb_private';out=ROOT/'output/research/pic_longitudinal/nested_improvement';out.mkdir(exist_ok=True)
    cohort=private/'landmarks.jsonl';rows=[json.loads(s) for s in cohort.read_text().splitlines()]
    for r in rows:
        if r['index_age_hours']>=r['first_culture_age_hours'] or any(max(e['age_hours'],e['available_age_hours'])>r['index_age_hours'] for e in r['events']):raise ValueError('Prediction timing violation')
    protocol={'stage':'further_development_on_exposed_cohort','clinical_ready':False,
        'source':'PIC v1.1.0','cohort_sha256':digest(cohort),'endpoint_unchanged':True,
        'seeds':[31,47,83],'outer_folds':3,'inner_folds':2,'selection_metric':'patient-weighted inner OOF AUPRC; candidate insertion order breaks ties',
        'candidates':CANDIDATES,'compact_features':COMPACT,'native_boost_weight_scale':'mean sample weight 1; all other candidates total weight 1 per infant',
        'preprocessing':'Training fold only; >=5 distinct observed infants per feature; infant-weighted scaling; fixed median, distance-weighted 5-NN, or native missingness; explicit missing indicators.',
        'knn_donors':'Training-fold landmarks only. Repeated donor landmarks may influence imputation; no synthetic or test donor rows.',
        'no_new_training_labels':True,'lab_predictors':'excluded: no verified result-availability timestamp',
        'emr_symptom_predictors':'excluded: NLP/document provenance and availability require separate review',
        'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'backend/ml/dynamic_features.py']},
        'packages':{p:importlib.metadata.version(p) for p in ['numpy','scikit-learn']}}
    path=out/'protocol.json'
    if path.exists() and json.loads(path.read_text())!=json.loads(json.dumps(protocol)):raise ValueError('Protocol drift')
    save(path,protocol)
    fs=[features(r['index_age_hours'],r['sex'],r['events']) for r in rows]
    matrices={name:np.array([[f[c] for c in cols] for f in fs],dtype=float) for name,cols in [('compact',COMPACT),('trend',GROUPS['trend'])]}
    y=np.array([r['label'] for r in rows]);groups=np.array([r['patient_id'] for r in rows]);w=weighting(rows)
    results=[];selection=[];oof_all={};inner_scores=[]
    for seed in protocol['seeds']:
        checkpoint=private/'nested_improvement'/f'seed{seed}.json'
        if checkpoint.exists():
            d=json.loads(checkpoint.read_text());preds={k:np.array(v) for k,v in d['predictions'].items()};selection+=d['selection'];inner_scores+=d['inner_scores']
        else:
            preds={k:np.zeros(len(rows)) for k in [*CANDIDATES,'nested_selected','training_prevalence']};ss=[];ii=[]
            for fold,(tr,ho) in enumerate(folds(rows,seed)):
                train_rows=[rows[i] for i in tr];tw=weighting(train_rows);inner=folds(train_rows,seed+100+fold,2)
                scores={}
                for name,spec in CANDIDATES.items():
                    x=matrices[spec[0]];ip=np.zeros(len(tr))
                    for a,b in inner:
                        ix=tr[a];jx=tr[b];iw=weighting([rows[i] for i in ix])
                        model=FoldModel(spec,seed).fit(x[ix],y[ix],groups[ix],iw)
                        ip[b]=model.predict(x[jx])
                    scores[name]=metrics(y[tr],ip,tw)['auprc']
                    ii.append({'seed':seed,'outer_fold':fold,'candidate':name,'inner_auprc':scores[name]})
                    model=FoldModel(spec,seed).fit(x[tr],y[tr],groups[tr],tw);preds[name][ho]=model.predict(x[ho])
                chosen=max(CANDIDATES,key=lambda n:scores[n])
                preds['nested_selected'][ho]=preds[chosen][ho];preds['training_prevalence'][ho]=np.average(y[tr],weights=tw)
                ss.append({'seed':seed,'outer_fold':fold,'selected':chosen,'inner_auprc':scores[chosen],
                    'training_infants':len(set(groups[tr])),'test_infants':len(set(groups[ho])),
                    'training_positive_infants':len(set(groups[tr][y[tr]==1])),'test_positive_infants':len(set(groups[ho][y[ho]==1])),'patient_overlap':0})
                print('Completed nested seed',seed,'fold',fold,'selected',chosen,flush=True)
            save(checkpoint,{'protocol_sha256':digest(path),'predictions':{k:v.tolist() for k,v in preds.items()},'selection':ss,'inner_scores':ii})
            selection+=ss;inner_scores+=ii
        for name,p in preds.items():
            results.append({'seed':seed,'method':name,'patients':len(set(groups)),'positive_patients':len(set(groups[y==1])),
                'landmarks':len(rows),**metrics(y,p,w),'max_score':float(p.max()),
                'interpretation':'nested selection procedure' if name=='nested_selected' else 'fixed candidate or baseline; no post-hoc promotion'})
        oof_all[seed]=preds
        write_csv(out/'metrics.csv',results);write_csv(out/'inner_selection.csv',selection);write_csv(out/'inner_scores.csv',inner_scores)
    intervals=[];paired=[]
    for name in ['nested_selected','compact_lr_median_C001','compact_lr_knn_C01','compact_native_missing_boost']:
        ci=clustered_ci(y,oof_all[31][name],rows)
        pair=clustered_ci(y,oof_all[31][name],rows,comparison=oof_all[31]['training_prevalence'])
        for metric,bounds in ci['intervals'].items():intervals.append({'method':name,'seed':31,'metric':metric,'low_95':bounds[0],'high_95':bounds[1],'resamples':2000,'skipped_single_class':ci['skipped_single_class']})
        for metric,bounds in pair['intervals'].items():paired.append({'method':name,'seed':31,'metric':metric,'comparison':'minus fold-training prevalence','low_95':bounds[0],'high_95':bounds[1],'resamples':2000})
    save(out/'results.json',{'protocol':protocol,'metrics':results,'selection':selection,'intervals':intervals,'paired':paired,'clinical_ready':False,
        'limitations':['Exposed development cohort, not a final independent test.','Only seven independent positive infants.','Culture-negative controls are not adjudicated uninfected infants.','Probabilities and action thresholds have no independent calibration or clinical validation.']})
    write_csv(out/'intervals.csv',intervals);write_csv(out/'paired_intervals.csv',paired)
    print('Nested model comparison complete; no app model replaced.',flush=True)


if __name__=='__main__':main()
