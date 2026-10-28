"""Read-only assessment; exports aggregates, never source patient rows."""
import hashlib,io,json,re,zipfile
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]


def main():
    source=Path('C:/Users/hadia/Downloads');out=ROOT/'output/research/candidate_data_audit';out.mkdir(exist_ok=True)
    book=source/'Sepsis Data 2.xlsx';w=pd.read_excel(book,sheet_name='Sheet1');w.columns=w.columns.str.strip()
    with zipfile.ZipFile(source/'5vdz5cftz7-1.zip') as z:d=pd.read_csv(z.open('deid-nicu-sepsis-tta.csv'))
    with zipfile.ZipFile(source/'1-s2.0-S2352340919311436-mmc1.zip') as z:contents=[{'filename':i.filename,'bytes':i.file_size} for i in z.infolist()]
    subsets=[]
    for label,mask in [('all',d.onset_age_in_days.notna()),('recorded_age_0_to_2_days',d.onset_age_in_days.between(0,2)),('recorded_age_0_to_28_days',d.onset_age_in_days.between(0,28))]:
        s=d.loc[mask];subsets.append({'subset':label,'episodes':len(s),'infants':int(s.unique_patient_id.nunique()),
            'sepsis_group_counts':{str(k):int(v) for k,v in s.sepsis_group.value_counts().items()},
            'bacteremic_episodes':int(s.blood_culture_positive.sum()),
            'bacteremic_infants':int(s.loc[s.blood_culture_positive==1].unique_patient_id.nunique())})
    report={'purpose':'Dataset suitability assessment only; no models trained or deployed',
        'source_sha256':{n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in ['Sepsis Data 2.xlsx','5vdz5cftz7-1.zip','1-s2.0-S2352340919311436-mmc1.zip']},
        'workbook':{'rows':len(w),'columns':len(w.columns),'unique_record_ids':int(w['PATIENT NO'].nunique()),
            'outcome_code_counts':{str(k):int(v) for k,v in w['CONTROL/CASE'].value_counts().items()},
            'figshare_md5_match':hashlib.md5(book.read_bytes()).hexdigest()=='4fce75c9e8cfbe4340991757a9ac97b4',
            'source':'https://doi.org/10.6084/m9.figshare.28395161.v1',
            'study':'https://f1000research.com/articles/14-390/v4',
            'reported_design':'69 culture-proven cases and 69 culture-negative, clinically non-septic controls; preterm case-control study',
            'missing_cells':int(w.isna().sum().sum()),
            'sepsis_signs_exact_outcome_copy':bool((w['SEPSIS SIGNS']==w['CONTROL/CASE']).all()),
            'patient_number_partitions_outcome':bool(pd.crosstab(w['CONTROL/CASE'],w['PATIENT NO']<=69).eq(0).any(axis=1).all()),
            'gestation_week_plus_days_strings':int(w['GESTATIONAL AGE'].astype(str).str.fullmatch(r'\s*\d+\s*\+\s*\d+\s*').sum()),
            'maternal_features':['age only; delivery mode is available as perinatal context'],
            'missing_for_eos':['infant-specific postnatal age at evaluation','sepsis-onset age','measurement/result-availability timestamps','serial observations','GBS/ROM/fever/intrapartum antibiotic timing'],
            'judgment':'Most promising supplied alternative for a separate small preterm diagnostic biomarker study, not yet an EOS longitudinal prediction dataset.'},
        'chop':{'source':'https://data.mendeley.com/datasets/5vdz5cftz7/1',
            'study':'https://pmc.ncbi.nlm.nih.gov/articles/PMC6881601/','columns':len(d.columns),'subsets':subsets,
            'median_recorded_onset_days':float(d.onset_age_in_days.median()),'maximum_recorded_onset_days':float(d.onset_age_in_days.max()),
            'repeated_patient_episodes':True,'serial_vital_or_lab_measurements_in_public_csv':False,
            'leakage_exclusions':['sepsis_group','blood_culture_positive','positive_days','cx_site','time_to_antibiotics','mortality outcomes','support-free days','length_of_stay_hours'],
            'temperature_caution':'Maximum temperature over the evaluation calendar day can include values after assessment; exclude from strict early prediction without raw timestamps.',
            'judgment':'Documented real registry with reviewed outcomes; only one bacteremic infant in recorded age 0–2-day subset, so not a stronger EOS event source than current PIC cohort.'},
        'supplement_zip':{'contents':contents,'patient_data_in_zip':False,'relationship':'Companion analysis/extraction scripts for the same CHOP study; not a third cohort. Raw PTN/PCORnet tables referenced by the scripts are not included.'},
        'pooling':'Do not concatenate these case-control and episode cohorts into PIC without distinct source/endpoint definitions, scope harmonization and source-separated validation.',
        'clinical_ready':False,'app_model_changed':False}
    (out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    md='''# Assessment of newly supplied neonatal datasets

The Excel workbook is the strongest new candidate for a small **preterm diagnostic biomarker** study. Its MD5 matches the public Figshare file exactly. The associated paper describes 69 culture-proven sepsis cases and 69 controls, providing more documented cases than the seven-positive-infant strict PIC forecasting cohort. These are different tasks; this does not establish superior predictive performance.

The workbook has 138 complete rows and 23 columns, including maternal age, gestation, delivery mode, birth weight and CBC components/derived indices. It has no infant-specific onset age or serial measurement/availability times. The paper describes sampling after 24 hours and before culture confirmation, which does not establish onset within 72 hours or pre-suspicion forecasting for every infant. A 50:50 selected case-control dataset cannot establish population prevalence or calibrated absolute EOS risk.

**Leakage risks:** SEPSIS SIGNS exactly duplicates CONTROL/CASE in every row. Patient number also partitions the outcome groups. Neither can be a predictor. Groupwise record numbers are not sufficient as globally unique infant IDs. Gestation strings must be parsed as weeks plus days (105 rows), not decimal weeks. Differential blood-count units, extreme values and derived-index definitions require reconciliation; values must not be silently corrected. Multiple indices derived from the same counts are not independent new measurements. Complete cells do not prove unbiased data collection.

The CHOP CSV contains 1,946 evaluations in 986 infants. There are 128 bacteremic episodes in 113 infants overall, but only one bacteremic infant among 302 evaluations with recorded onset age 0–2 days. Median onset age is 44 days and the maximum is 335 days. Thus the full registry cannot be treated as EOS. Labels were manually reviewed and include distinct culture-negative, clinical, fungal and viral categories. Multiple episodes require patient-grouped splits. The public file contains episode summaries, not raw longitudinal vital signs or laboratory series. Evaluation-day maximum temperature can include future measurements.

The small supplementary ZIP contains two R scripts and no patient table. Those scripts belong to the same CHOP study and reference raw PTN/PCORnet files that are not supplied. Their availability does not provide another training cohort.

Recommendation: retain PIC for real longitudinal method development; evaluate the Excel data separately as preterm diagnostic research after resolving timing, code meanings and units. Obtain exact onset/assessment ages and timestamped laboratory availability before describing that model as EOS forecasting. Use CHOP for separately defined broader infant-sepsis/process studies, not to inflate EOS counts. No model or app was changed by this inspection.

Sources:
- Workbook: https://doi.org/10.6084/m9.figshare.28395161.v1
- Workbook study: https://f1000research.com/articles/14-390/v4
- CHOP registry: https://data.mendeley.com/datasets/5vdz5cftz7/1
- CHOP data dictionary: https://pmc.ncbi.nlm.nih.gov/articles/PMC6881601/

assessment.json contains file hashes and reproducible aggregate counts. No patient-level rows are included in this report.
'''
    (out/'assessment.md').write_text(md,encoding='utf8');print(json.dumps({'assessment':str(out/'assessment.md'),'patient_rows_exported':False,'workbook_source_verified':report['workbook']['figshare_md5_match']}))


if __name__=='__main__':main()
