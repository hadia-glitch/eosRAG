"""Causal landmark extraction from PIC v1.1.0, entirely on the local computer.

The endpoint is a documented pathogen in an early blood culture, NOT an
adjudicated EOS diagnosis. Restricted patient rows go only into data/ (ignored).
No diagnoses, microbiology, prescriptions or future measurements are predictors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
try:
    from ml.dynamic_contract import BOUNDS,VERSION,available_events
except ModuleNotFoundError:
    from backend.ml.dynamic_contract import BOUNDS,VERSION,available_events

ROOT = Path(__file__).resolve().parents[2]
SEED = 31
VITALS = {'1001': 'neonatal_temperature', '1003': 'heart_rate',
          '1004': 'respiratory_rate', '1006': 'spo2', '1002':'pulse_rate',
          '1015':'diastolic_pressure', '1016':'systolic_pressure', '1014':'measured_weight_kg'}
CORE_VITALS = {'neonatal_temperature','heart_rate','respiratory_rate','spo2','pulse_rate'}
# Conservative engineering phenotype. All assignments require clinical review.
# Preliminary Gram findings, fungi and possible skin/oral flora stay ambiguous.
PATHOGENS = {'escherichia coli', 'listeria monocytogenes', 'klebsiella pneumoniae',
             'streptococcus agalactiae group b', 'enterococcus faecium group d',
             'streptococcus gallolyticus', 'staphylococcus aureus',
             'pseudomonas aeruginosa', 'enterobacter cloacae'}
NEGATIVE = {'no bacterial growth for 5-day culture',
            'cultured for 5 days without bacteria, fungus growth',
            'no bacterial growth', 'no bacteria, fungus growth'}
MISSING_MATERNAL = ['maternal_temperature', 'rom_hours', 'gbs_positive',
                    'adequate_intrapartum_antibiotics', 'clinical_chorioamnionitis']
OFFSETS = [1., 3., 6., 12., 24., 36., 48.]


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf8')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024**2), b''): h.update(block)
    return h.hexdigest()


def organism_class(label):
    text = str(label).strip().lower()
    if text in PATHOGENS: return 'pathogen'
    if text in NEGATIVE: return 'explicit_bacterial_negative'
    return 'ambiguous_or_nonbacterial'


def outcome(rows):
    """Do not label an absent, fungus-only or preliminary result negative."""
    classes = {organism_class(x) for x in rows}
    if 'pathogen' in classes: return 1
    if classes == {'explicit_bacterial_negative'}: return 0
    return None


def main(archive, private, public):
    private = private.resolve(); public = public.resolve()
    if not private.is_relative_to((ROOT/'data').resolve()):
        raise ValueError('Patient-level outputs must stay inside ignored data/')
    private.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        prefix = 'paediatric-intensive-care-database-1.1.0/V1.1.0/'
        def read(table, **kwargs): return pd.read_csv(z.open(prefix+table+'.csv'), **kwargs)
        patients = read('PATIENTS'); admissions = read('ADMISSIONS')
        dictionary = read('D_ITEMS', dtype={'ITEMID': str})
        microbiology = read('MICROBIOLOGYEVENTS', dtype={'ORG_ITEMID': str})
        if patients.SUBJECT_ID.duplicated().any() or admissions.HADM_ID.duplicated().any():
            raise ValueError('Duplicate patient/admission master IDs')
        patients['DOB'] = pd.to_datetime(patients.DOB, errors='raise')
        for col in ['ADMITTIME', 'DISCHTIME']: admissions[col] = pd.to_datetime(admissions[col], errors='raise')
        master = admissions.merge(patients[['SUBJECT_ID', 'DOB', 'GENDER']], on='SUBJECT_ID', validate='many_to_one')
        master['admission_age'] = (master.ADMITTIME-master.DOB).dt.total_seconds()/3600
        eligible = master.loc[master.admission_age.between(0,72,inclusive='left')].copy()
        # The first eligible admission per infant is the only source admission.
        eligible = eligible.sort_values('ADMITTIME').drop_duplicates('SUBJECT_ID')
        m = microbiology.merge(master[['SUBJECT_ID','HADM_ID','DOB','ADMITTIME','DISCHTIME']],
                              on=['SUBJECT_ID','HADM_ID'], validate='many_to_one')
        m['CHARTTIME'] = pd.to_datetime(m.CHARTTIME, errors='coerce')
        m['age'] = (m.CHARTTIME-m.DOB).dt.total_seconds()/3600
        m = m.loc[m.SPEC_TYPE_DESC.str.contains('血培养',na=False) & m.age.between(0,72,inclusive='left')]
        m = m.merge(dictionary[['ITEMID','LABEL']].rename(columns={'ITEMID':'ORG_ITEMID','LABEL':'organism_en'}),
                    on='ORG_ITEMID', how='left', validate='many_to_one')
        # Materially inconsistent or preadmission collections are not silently
        # shifted to admission. Exclude them from this hospital-landmark cohort.
        invalid = set(m.loc[(m.CHARTTIME<m.ADMITTIME)|(m.CHARTTIME>m.DISCHTIME),'HADM_ID'])
        labels = {}; label_counts = Counter()
        for hadm, rows in m.groupby('HADM_ID'):
            if hadm in invalid: continue
            result = outcome(rows.organism_en)
            label_counts[str(result)] += 1
            if result is not None:
                labels[int(hadm)] = {'label':result, 'first_culture_age':float(rows.age.min())}
        hadms = set(eligible.HADM_ID) & labels.keys()
        events = {}; chart_audit = Counter(); units = Counter()
        columns = ['SUBJECT_ID','HADM_ID','ITEMID','CHARTTIME','STORETIME','VALUENUM','VALUEUOM']
        reference = eligible.set_index('HADM_ID')
        for block in read('CHARTEVENTS', usecols=columns, dtype={'ITEMID':str}, chunksize=250000):
            chart_audit['scanned'] += len(block)
            b = block.loc[block.HADM_ID.isin(hadms)&block.ITEMID.isin(VITALS)].copy()
            if b.empty: continue
            b = b.merge(eligible[['HADM_ID','SUBJECT_ID','DOB','ADMITTIME','DISCHTIME']],
                        on=['SUBJECT_ID','HADM_ID'], validate='many_to_one')
            for col in ['CHARTTIME','STORETIME']: b[col] = pd.to_datetime(b[col], errors='coerce')
            valid_times = b.CHARTTIME.notna() & b.STORETIME.notna()
            chart_audit['missing_measurement_or_availability_time'] += int((~valid_times).sum())
            b = b.loc[valid_times].copy()
            b['age'] = (b.CHARTTIME-b.DOB).dt.total_seconds()/3600
            b['available_age'] = (b[['CHARTTIME','STORETIME']].max(axis=1)-b.DOB).dt.total_seconds()/3600
            b['number'] = pd.to_numeric(b.VALUENUM, errors='coerce')
            for row in b.itertuples(index=False):
                key = VITALS[row.ITEMID]; lo,hi = BOUNDS[key]
                units[(key,str(row.VALUEUOM))] += 1
                if not np.isfinite(row.number) or not lo<=row.number<=hi:
                    chart_audit['unusable_numeric_or_range'] += 1; continue
                expected = {'neonatal_temperature':{'°C','℃','C','°c'}, 'heart_rate':{'bpm'},
                            'respiratory_rate':{'insp/min','bpm'}, 'spo2':{'%'},'pulse_rate':{'bpm'},
                            'diastolic_pressure':{'mmHg'},'systolic_pressure':{'mmHg'},'measured_weight_kg':{'kg'}}[key]
                if str(row.VALUEUOM).strip() not in expected:
                    chart_audit['unrecognized_unit'] += 1; continue
                if not 0<=row.age<72 or row.CHARTTIME<row.ADMITTIME or row.CHARTTIME>row.DISCHTIME:
                    chart_audit['outside_birth_admission_window'] += 1; continue
                events.setdefault(int(row.HADM_ID),[]).append({'age_hours':float(row.age),
                    'available_age_hours':float(row.available_age), 'field':key,'value':float(row.number)})
        records=[]; exclusions=Counter(); per_offset=Counter(); midnight=0
        for row in eligible.itertuples(index=False):
            if row.HADM_ID not in labels: exclusions['no_unambiguous_early_blood_culture_endpoint']+=1; continue
            label=labels[row.HADM_ID]
            raw=events.get(row.HADM_ID,[])
            # Deduplicate identical chart rows; do not fabricate extra observations.
            raw=[dict(zip(['age_hours','available_age_hours','field','value'],key))
                 for key in sorted({(e['age_hours'],e['available_age_hours'],e['field'],e['value']) for e in raw})]
            if row.DOB.hour==row.DOB.minute==row.DOB.second==0:midnight+=1
            for offset in OFFSETS:
                index=float(row.admission_age+offset)
                if index>=72 or row.ADMITTIME+pd.Timedelta(hours=offset)>=row.DISCHTIME: continue
                if index>=label['first_culture_age']:
                    exclusions['landmark_at_or_after_first_culture']+=1; continue
                observed=available_events(raw,index)
                recent={e['field'] for e in observed if e['age_hours']>=index-6 and e['field'] in CORE_VITALS}
                if len(recent)<2: exclusions['landmark_fewer_than_two_recent_vitals']+=1; continue
                pid=hashlib.sha256(f'pic-v1.1.0:{row.SUBJECT_ID}'.encode()).hexdigest()
                records.append({'patient_id':pid,'landmark_offset_hours':offset,'index_age_hours':index,
                    'label':label['label'],'first_culture_age_hours':label['first_culture_age'],
                    'sex':row.GENDER if row.GENDER in {'M','F'} else None,
                    'birth_time_midnight':row.DOB.hour==row.DOB.minute==row.DOB.second==0,
                    'events':observed})
                per_offset[f'{offset:g}h_label{label["label"]}']+=1
        target=private/'landmarks.jsonl'
        with target.open('w',encoding='utf8') as f:
            for r in records:f.write(json.dumps(r,allow_nan=False)+'\n')
        units_public=[{'field':f,'unit':u,'rows':n} for (f,u),n in sorted(units.items())]
        by_patient={r['patient_id']:r['label'] for r in records}
        protocol={'feature_version':VERSION,'seed':SEED,'dataset':'PIC v1.1.0',
            'dataset_url':'https://physionet.org/content/picdb/1.1.0/',
            'archive_sha256':digest(archive),'zip_table_prefix':prefix,
            'target':'Subsequent documented named bacterial pathogen in blood collected before 72 postnatal hours; unadjudicated research phenotype',
            'clinical_eos_eligible':False,'label_adjudicated':False,
            'landmark_offsets_after_admission_hours':OFFSETS,'lookback_hours':24,'recent_vital_window_hours':6,
            'eligibility':'First admission before 72h, explicit bacterial no-growth or named-pathogen early culture, prediction strictly before first early blood culture, >=2 distinct vitals recorded and available in prior 6h.',
            'availability':'max(CHARTTIME, STORETIME) <= landmark; missing STORETIME excluded',
            'unit_context':'ITEMID 1004 is Respiratory Rate in D_ITEMS. Its csv bpm is interpreted as breaths/minute by this item identity, not as heart rate. Pulse (1002) remains a distinct measurement from Heart Rate (1003). Measured weight is not relabelled birth weight.',
            'outcome_policy':'Named pathogen overrides other reports. Otherwise every report must explicitly exclude bacteria. Unresolved Gram reports, possible contaminants, fungi, missing and fungus-only negatives are excluded.',
            'positive_organism_allowlist':sorted(PATHOGENS),'explicit_bacterial_negatives':sorted(NEGATIVE),
            'inputs':list(BOUNDS),'missing_maternal_predictors':MISSING_MATERNAL,
            'never_predictors':['diagnoses','culture results','organism','prescriptions','death','discharge','length of stay','patient identifiers','absolute shifted dates'],
            'laboratory_policy':'Excluded: no result-availability timestamp in LABEVENTS. CHARTTIME alone cannot establish prospective availability.',
            'split_policy':'Patient-disjoint; shifted calendar dates are not a real chronological validation split.',
            'code_sha256':digest(Path(__file__))}
        report={'protocol':protocol,'all_patients':len(patients),'all_admissions':len(master),
            'admissions_age_0_72h':int(master.admission_age.between(0,72,inclusive='left').sum()),
            'first_eligible_admissions':len(eligible),'negative_age_admissions_excluded':int(master.admission_age.lt(0).sum()),
            'blood_culture_admission_classification':dict(label_counts),'inconsistent_collection_admissions_excluded':len(invalid),
            'labelled_admissions_with_birth_before72h':len(hadms),'landmarks':len(records),'patients':len(by_patient),
            'positive_patients':sum(by_patient.values()),'negative_patients':len(by_patient)-sum(by_patient.values()),
            'positive_landmarks':sum(r['label'] for r in records),'per_offset':dict(per_offset),
            'excluded':dict(exclusions),'chart_audit':dict(chart_audit),'observed_units':units_public,
            'birth_times_at_midnight_among_master_patients':float((patients.DOB.dt.hour.eq(0)&patients.DOB.dt.minute.eq(0)).mean()),
            'private_cohort_sha256':digest(target),
            'limitations':['No clinical phenotype/contaminant adjudication; controls are culture-negative, not proven free of sepsis.',
                'Conditioning on culture testing and survival to landmarks causes selection bias; hospital-only cohort.',
                'Midnight birth times may be date-only; sensitivity analysis excludes them.',
                'Gestation, birthweight and linked maternal fields are not supplied as structured predictors in these selected tables.',
                'Repeated landmarks increase rows, not the number of independent positive infants.',
                'No result time for microbiology; only collection-time phenotype is used, never outcome availability as a predictor.']}
        save(public/'cohort_audit.json',report);save(public/'protocol.json',protocol)
        print(json.dumps({k:report[k] for k in ['landmarks','patients','positive_patients','negative_patients','positive_landmarks','per_offset','chart_audit','excluded']},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--private',type=Path,default=ROOT/'data/picdb_private')
    p.add_argument('--output',type=Path,default=ROOT/'output/research/pic_longitudinal')
    a=p.parse_args();main(a.archive,a.private,a.output)
