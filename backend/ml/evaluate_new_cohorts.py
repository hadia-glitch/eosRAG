"""Separate diagnostic research cohorts; no pooled or deployed EOS probability.

--prepare uses bundled pandas for read-only workbook extraction. Training is
local; only aggregate results leave ignored data/. No source code is executed.
"""
import argparse,hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
PRIVATE=ROOT/'data/new_neonatal_cohorts';OUT=ROOT/'output/research/new_neonatal_cohorts'


def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf8')


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def gestation(value):
    parts=str(value).strip().split('+')
    if len(parts)==2:
        weeks,days=map(int,parts)
        if not 0<=days<=6:raise ValueError('Invalid gestational days')
        return weeks+days/7
    return float(value)


def prepare():
    import pandas as pd
    source=Path('C:/Users/hadia/Downloads');book=source/'Sepsis Data 2.xlsx'
    w=pd.read_excel(book,sheet_name='Sheet1');w.columns=w.columns.str.strip()
    if not w['PATIENT NO'].is_unique or set(w['CONTROL/CASE'])!={1,2}:raise ValueError('Workbook patient/label contract changed')
    if not (w['SEPSIS SIGNS']==w['CONTROL/CASE']).all():raise ValueError('Previously identified copy changed; re-audit')
    maternal=['maternal_age','sex_female','gestation_weeks','delivery_cesarean','birth_weight_kg','small_for_gestation','large_for_gestation']
    blood=['log_total_count','monocyte_reported','neutrophil_reported','log_platelets','lymphocyte_reported']
    indices=['SII (SYSTEMIC IMMUNE INFLAMMATORY INDEX)','SIRI (SYSTEMIC INFLAMMATION RESPONSE INDEX)','PIV (PAN IMMUNE INFLAMMATION VALUE)','NLR (NEUTROPHIL TO LYMPHOCYTE RATIO)','PLR (PLATELET TO LYMPHOCYTE RATIO)','MLR (MONOCYTE TO LYMPHOCYTE RATIO)']
    import math
    records=[]
    for _,r in w.iterrows():
        x=[float(r['AGE OF MOTHER']),float(r['SEX OF CHILD']==2),gestation(r['GESTATIONAL AGE']),float(r['MODE OF DELIVERY']==2),float(r['BIRTH WEIGHT']),float(r['SGA/AGA/LGA']==1),float(r['SGA/AGA/LGA']==3),math.log1p(r['TOTAL COUNT']),float(r['MONOCYTE']),float(r['NEUTROPHIL']),math.log1p(r['PLATELET']),float(r['LYMPHOCYTE'])]
        if not all(math.isfinite(v) for v in x):raise ValueError('Unexpected workbook value')
        records.append({'group':hashlib.sha256(f'workbook:{r["PATIENT NO"]}'.encode()).hexdigest(),'label':int(r['CONTROL/CASE']==2),'x':x})
    save(PRIVATE/'workbook.json',{'features':maternal+blood,'baseline_features':list(range(len(maternal))),'records':records,
        'source_sha256':digest(book),'scope':'Preterm case-control culture-positive diagnosis; individual EOS timing unavailable.',
        'exclusions':['PATIENT NO','PATIENT NO GROUPWISE','SEPSIS SIGNS','PRETERM CATEGORY','BIRTHWEIGHT CLASSIFICATION',*indices],
        'notes':'No counts silently corrected. log1p limits influence of extreme counts. Six derived indices excluded to avoid redundant unverified units; their underlying counts retained.'})
    with zipfile.ZipFile(source/'5vdz5cftz7-1.zip') as z:d=pd.read_csv(z.open('deid-nicu-sepsis-tta.csv'))
    allowed=['sex','gestational_age_at_birth_weeks','birth_weight_kg','onset_age_in_days','intubated_at_time_of_sepsis_evaluation','inotrope_at_time_of_sepsis_eval','central_venous_line','umbilical_arterial_line','ecmo','comorbidity_necrotizing_enterocolitis','comorbidity_chronic_lung_disease','comorbidity_cardiac','comorbidity_surgical','comorbidity_ivh_or_shunt']
    s=d.loc[d.onset_age_in_days.between(0,28,inclusive='left')&((d.blood_culture_positive==1)|(d.sepsis_group==2))].copy()
    rows=[{'group':hashlib.sha256(f'chop:{r["unique_patient_id"]}'.encode()).hexdigest(),'label':int(r['blood_culture_positive']),
        'x':[None if pd.isna(r[c]) else float(r[c]) for c in allowed]} for _,r in s.iterrows()]
    save(PRIVATE/'chop.json',{'features':allowed,'baseline_features':[0,1,2,3],'records':rows,'source_sha256':digest(source/'5vdz5cftz7-1.zip'),
        'scope':'Age <28 days; bacteremia versus manually classified culture-negative rule-out episodes; conditional on sepsis evaluation, not EOS forecasting.',
        'exclusions':[c for c in d.columns if c not in allowed and c not in ['unique_patient_id','blood_culture_positive']],
        'notes':'Outcome fields and IDs never enter matrix. Clinical sepsis, fungal/viral groups, other groups and non-blood culture-positive cases are excluded, not labelled healthy. Evaluation-day maximum temperature and treatment/outcome measures excluded. Support/comorbidities are recorded at/before evaluation, not a pre-evaluation forecast.'})
    print('Two private feature cohorts prepared; originals unchanged.',flush=True)


def run():
    import csv,collections,importlib.metadata
    import numpy as np
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import confusion_matrix,roc_auc_score,average_precision_score,brier_score_loss
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier,ExtraTreesClassifier,HistGradientBoostingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    import joblib
    candidates=['lr_C01','lr_C1','forest','extra_trees','boost']
    protocol={'stage':'exploratory_diagnostic_development','seeds':[31,47,83],'outer_folds':5,'inner_folds':3,
        'candidate_selection':'maximum inner patient-weighted AUROC; insertion order tie break','candidates':candidates,
        'threshold_selection':'inner-OOF maximum balanced accuracy over fixed grid 0.05:0.01:0.95; largest threshold breaks ties',
        'bootstrap':'2000 resamples of independent infants, seed31; all episodes of resampled infant retained',
        'training':'median imputation and scaling fitted within training fold; equal total weight per infant',
        'clinical_ready':False,'code_sha256':digest(Path(__file__)),
        'prepared_cohort_sha256':{n:digest(PRIVATE/f'{n}.json') for n in ['workbook','chop']},
        'packages':{p:importlib.metadata.version(p) for p in ['numpy','scikit-learn']}}
    path=OUT/'protocol.json'
    if path.exists() and json.loads(path.read_text())!=protocol:raise ValueError('Protocol drift')
    save(path,protocol)
    def weight(g):
        n=collections.Counter(g);return np.array([1/n[i] for i in g])
    def split(y,g,seed,n):
        ids=np.array(sorted(set(g)));labels=np.array([max(y[g==i]) for i in ids]);out=[]
        for a,b in StratifiedKFold(n,shuffle=True,random_state=seed).split(ids,labels):
            tr=np.flatnonzero(np.isin(g,ids[a]));te=np.flatnonzero(np.isin(g,ids[b]));assert not set(g[tr])&set(g[te]);out.append((tr,te))
        return out
    def model(name,seed):
        if name.startswith('lr'):m=LogisticRegression(C=.1 if name=='lr_C01' else 1.,max_iter=3000,random_state=seed)
        elif name=='boost':m=HistGradientBoostingClassifier(max_iter=60,max_leaf_nodes=3,min_samples_leaf=12,l2_regularization=5,early_stopping=False,random_state=seed)
        else:
            cls=RandomForestClassifier if name=='forest' else ExtraTreesClassifier
            m=cls(n_estimators=120,max_depth=3,min_samples_leaf=8,max_features=.8,n_jobs=2,random_state=seed)
        return make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),m)
    def fit(name,x,y,g,seed):
        m=model(name,seed);kw={list(m.named_steps)[-1]+'__sample_weight':weight(g)};return m.fit(x,y,**kw)
    def measure(y,p,decision,w):
        tn,fp,fn,tp=confusion_matrix(y,decision,labels=[0,1],sample_weight=w).ravel()
        return {'auroc':float(roc_auc_score(y,p,sample_weight=w)),'auprc':float(average_precision_score(y,p,sample_weight=w)),
            'accuracy':float((tp+tn)/(tp+tn+fp+fn)),'sensitivity':float(tp/(tp+fn)),'specificity':float(tn/(tn+fp)),
            'precision':float(tp/(tp+fp)) if tp+fp else None,'brier':float(brier_score_loss(y,p,sample_weight=w))}
    def threshold(y,p,w):
        def objective(t):
            tn,fp,fn,tp=confusion_matrix(y,p>=t,labels=[0,1],sample_weight=w).ravel()
            return ((tn/(tn+fp)+tp/(tp+fn))/2,t)
        return max(np.linspace(.05,.95,91),key=objective)
    allrows=[];intervals=[];contrasts=[];counts=[];selections=[]
    for dataset in ['workbook','chop']:
        (PRIVATE/dataset).mkdir(parents=True,exist_ok=True)
        data=json.loads((PRIVATE/f'{dataset}.json').read_text());records=data['records'];x=np.array([r['x'] for r in records],dtype=float);y=np.array([r['label'] for r in records]);g=np.array([r['group'] for r in records]);w=weight(g)
        counts.append({'dataset':dataset,'rows':len(y),'infants':len(set(g)),'positive_rows':int(y.sum()),'positive_infants':len(set(g[y==1])),'scope':data['scope']})
        for seed in protocol['seeds']:
            checkpoint=PRIVATE/dataset/f'seed{seed}.json'
            if checkpoint.exists():
                saved=json.loads(checkpoint.read_text());assert saved['protocol_sha256']==digest(path)
                p={k:np.array(v) for k,v in saved['p'].items()};dec={k:np.array(v) for k,v in saved['decision'].items()};selections+=saved['selections']
            else:
                p={k:np.zeros(len(y)) for k in [*candidates,'nested_selected','demographic_baseline']};dec={k:np.zeros(len(y),dtype=bool) for k in p};ss=[]
                for fold,(tr,te) in enumerate(split(y,g,seed,5)):
                    inner=split(y[tr],g[tr],seed+100+fold,3);scores={};thresholds={}
                    for name in [*candidates,'demographic_baseline']:
                        kind='lr_C01' if name=='demographic_baseline' else name
                        xx=x[:,data['baseline_features']] if name=='demographic_baseline' else x
                        ip=np.zeros(len(tr))
                        for a,b in inner:
                            fitted=fit(kind,xx[tr[a]],y[tr[a]],g[tr[a]],seed);ip[b]=fitted.predict_proba(xx[tr[b]])[:,1]
                        scores[name]=roc_auc_score(y[tr],ip,sample_weight=weight(g[tr]));thresholds[name]=threshold(y[tr],ip,weight(g[tr]))
                        fitted=fit(kind,xx[tr],y[tr],g[tr],seed);p[name][te]=fitted.predict_proba(xx[te])[:,1];dec[name][te]=p[name][te]>=thresholds[name]
                        if seed==31:joblib.dump(fitted,PRIVATE/dataset/f'fold{fold}_{name}.joblib')
                    chosen=max(candidates,key=lambda n:scores[n]);p['nested_selected'][te]=p[chosen][te];dec['nested_selected'][te]=dec[chosen][te]
                    ss.append({'dataset':dataset,'seed':seed,'fold':fold,'selected':chosen,'inner_auroc':float(scores[chosen]),'threshold':float(thresholds[chosen]),'patient_overlap':0,
                        'training_infants':len(set(g[tr])),'test_infants':len(set(g[te])),'test_positive_infants':len(set(g[te][y[te]==1]))})
                    print(dataset,'seed',seed,'fold',fold,'selected',chosen,flush=True)
                save(checkpoint,{'protocol_sha256':digest(path),'p':{k:v.tolist() for k,v in p.items()},'decision':{k:v.tolist() for k,v in dec.items()},'selections':ss});selections+=ss
            for name in p:allrows.append({'dataset':dataset,'seed':seed,'method':name,**measure(y,p[name],dec[name],w)})
            if seed==31:
                rng=np.random.default_rng(31);ixs=[np.flatnonzero(g==i) for i in sorted(set(g))];dist={k:[] for k in ['nested_selected','demographic_baseline']};paired=[];skipped=0
                for _ in range(2000):
                    ix=np.concatenate([ixs[i] for i in rng.integers(0,len(ixs),len(ixs))])
                    if len(set(y[ix]))<2:skipped+=1;continue
                    estimates={k:measure(y[ix],p[k][ix],dec[k][ix],w[ix]) for k in dist}
                    for k in dist:dist[k].append(estimates[k])
                    paired.append(estimates['nested_selected']['auroc']-estimates['demographic_baseline']['auroc'])
                for name,values in dist.items():
                    for metric in values[0]:
                        valid=[v[metric] for v in values if v[metric] is not None];lo,hi=np.quantile(valid,[.025,.975]) if valid else (None,None)
                        intervals.append({'dataset':dataset,'method':name,'metric':metric,'low_95':lo,'high_95':hi,'resamples':2000,'skipped_single_class':skipped})
                lo,hi=np.quantile(paired,[.025,.975]);contrasts.append({'dataset':dataset,'contrast':'nested-selected minus demographic baseline AUROC','mean':next(r['auroc'] for r in allrows if r['dataset']==dataset and r['seed']==31 and r['method']=='nested_selected')-next(r['auroc'] for r in allrows if r['dataset']==dataset and r['seed']==31 and r['method']=='demographic_baseline'),'low_95':lo,'high_95':hi})
            save(OUT/'progress.json',{'dataset':dataset,'seed_completed':seed})
            for filename,rows in [('metrics.csv',allrows),('intervals.csv',intervals),('paired_auroc.csv',contrasts),('selections.csv',selections),('cohort_counts.csv',counts)]:
                with (OUT/filename).open('w',newline='',encoding='utf8') as f:
                    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        print('Completed cohort',dataset,flush=True)
    save(OUT/'results.json',{'protocol':protocol,'cohorts':counts,'metrics':allrows,'intervals':intervals,'paired':contrasts,'clinical_ready':False,'independent_external_validation':False,'app_model_changed':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    prepare() if args.prepare else run()
