"""Author consistent longitudinal development cases, never clinical outcome labels.

Original pilot gold and cases remain immutable. Ten template families generate
100 dependent development cases; they are not 100 independent validation cases.
"""
import hashlib,json,random
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/synthetic_eos_v2'
FAMILIES=['well_single_risk','respiratory_deterioration','symptomatic_culture_unknown',
 'renal_impairment','severe_beta_lactam_allergy','stop_review_incomplete',
 'stop_review_reassuring','falling_crp_unwell','preterm_birth_context','referral_constraints']
SOURCES={'NICE':'https://www.nice.org.uk/guidance/ng195',
 'AAP_TERM':'https://publications.aap.org/pediatrics/article/142/6/e20182894/37522',
 'AAP_PRETERM':'https://publications.aap.org/pediatrics/article/142/6/e20182896/37519',
 'WHO':'https://www.who.int/publications/i/item/9789240102903'}
UNITS={'heart_rate':'beats/min','respiratory_rate':'breaths/min','temperature':'degC','spo2':'%',
 'mean_arterial_pressure':'mmHg','inspired_oxygen':'fraction','wbc':'10^9/L','crp':'mg/L',
 'pct':'ng/mL','platelets':'10^9/L','lactate':'mmol/L','hemoglobin':'g/dL',
 'creatinine':'mg/dL','urine_output':'mL/kg/hour'}

def main():
    rng=random.Random(20261025);cases=[];base=datetime(2026,1,1,tzinfo=timezone.utc)
    for index in range(100):
        family=FAMILIES[index//10];variant=index%10
        guideline=['NICE','AAP','WHO'][index%3]
        preterm=family=='preterm_birth_context'
        ga=round(rng.uniform(29,34) if preterm else rng.uniform(35,40.8),1)
        bw=round(rng.uniform(1.15,2.2) if preterm else rng.uniform(2.3,3.9),2)
        sex=rng.choice(['Female','Male']);delivery=rng.choice(['Vaginal','Cesarean'])
        if preterm and variant%2==0:delivery='Cesarean'
        stop=family.startswith('stop_review');age=48. if stop else 60. if family=='referral_constraints' and variant==5 else float(12+variant%4*6)
        birth=base+timedelta(days=index);assess=birth+timedelta(hours=age)
        sick=family in ['respiratory_deterioration','symptomatic_culture_unknown','renal_impairment','severe_beta_lactam_allergy','falling_crp_unwell','referral_constraints']
        symptoms=[]
        if sick:symptoms=['respiratory_distress']
        elif family=='stop_review_incomplete' and variant%2:symptoms=['persistent_respiratory_distress']
        referral_feasible=None;setting='hospital'
        if guideline=='WHO' and family=='referral_constraints':
            setting='community';referral_feasible=bool(variant%2)
            if variant==2:ga,bw=32.,1.35
        culture_status='unknown';culture_collected=None;culture_available=None;antibiotic_started=None
        initial_suspicion='unknown'
        if stop:
            culture_collected=(birth+timedelta(hours=3)).isoformat()
            antibiotic_started=(birth+timedelta(hours=4)).isoformat()
            if family=='stop_review_reassuring':
                culture_status='negative';culture_available=(birth+timedelta(hours=40)).isoformat();initial_suspicion='not_strong'
        observations=[]
        for point,hour in enumerate([max(1,age-8),age-4,age]):
            worsening=family=='respiratory_deterioration'
            hr=(148+point*14 if worsening else 169 if sick else 143)+rng.uniform(-3,3)
            rr=(48+point*12 if worsening else 68 if sick or symptoms else 44)+rng.uniform(-2,2)
            sat=(98-point*3 if worsening else 93 if sick else 98)+rng.uniform(-.5,.5)
            crp=(18-point*6 if family in ['falling_crp_unwell','stop_review_reassuring'] else 5+point*7 if worsening else 18 if sick else 3)+rng.uniform(-.5,.5)
            data={'heart_rate':round(hr,1),'respiratory_rate':round(rr,1),'temperature':round(37.8 if sick else 36.9,1),
                'spo2':round(sat,1),'mean_arterial_pressure':round(rng.uniform(35,48) if preterm else rng.uniform(40,55),1),
                'inspired_oxygen':round(.30 if sick else .21,2),'wbc':round(rng.uniform(8,23),1),
                'crp':round(crp,1),'pct':round(rng.uniform(.2,2.2),2),'platelets':round(rng.uniform(130,300),1),
                'lactate':round(rng.uniform(1.2,3.2) if sick else rng.uniform(.8,1.8),2),
                'hemoglobin':round(rng.uniform(13,18),1),'creatinine':1.7 if family=='renal_impairment' else .6,
                'urine_output':.3 if family=='renal_impairment' else 1.8}
            # Intentional, documented unknowns; no future results at assessment.
            if family=='symptomatic_culture_unknown' and point==2:data['pct']=None
            observed=birth+timedelta(hours=hour)
            observations.append({'observation_id':f'SYN2-{index+1:03}-O{point+1}',
                'age_hours':hour,'observed_at':observed.isoformat(),
                'available_at':(observed+timedelta(minutes=5) if point<2 else observed).isoformat(),
                'measurements':data})
        expected=['Preserve unknown facts and exact source citations.','Do not present a supplied-label classifier score as clinical EOS probability.',
            'Use only measurements available by the assessment time.','Separate observed trends from recommendations.']
        if family in ['respiratory_deterioration','falling_crp_unwell']:expected.append('Recognize worsening/persistent respiratory findings; a falling CRP alone cannot establish recovery.')
        if family=='renal_impairment':expected.append('Flag aminoglycoside renal-safety review; do not issue an automatic dose or invent a supported substitute.')
        if family=='severe_beta_lactam_allergy':expected.append('Preserve the explicitly recorded immediate severe allergy; seek qualified regimen review instead of an unsupported substitution.')
        if family=='stop_review_incomplete':expected.append('Do not conclude that antibiotic stopping criteria are fulfilled with missing culture/initial-suspicion information.')
        if family=='stop_review_reassuring':expected.append('Apply the active guideline stopping conditions and documented timing together; never turn a research score into a treatment order.')
        if guideline=='WHO' and setting=='community':expected.append('Keep hospital referral first and condition any outside-hospital pathway on explicit referral feasibility and source scope.')
        if guideline=='WHO' and setting=='community' and (bw<1.5 or variant==5):expected.append('Do not generalize an outpatient trial regimen to a low-birth-weight or recently hospitalized infant excluded by the source population.')
        if guideline=='AAP':expected.append('Select the gestational-age-appropriate AAP source and birth-context interpretation; do not mix preterm and term strategies.')
        case={'case_id':f'SYN2-{index+1:03}','synthetic':True,'family':family,'variant':variant+1,
            'active_guideline':guideline,'guideline_scope':('AAP_PRETERM' if ga<35 else 'AAP_TERM') if guideline=='AAP' else guideline,
            'care_setting':setting,'referral_feasible':referral_feasible,'birth_time':birth.isoformat(),'assessment_time':assess.isoformat(),
            'demographics':{'gestational_age_weeks':ga,'birth_weight_kg':bw,'sex':sex,'delivery_mode':delivery,'apgar_5_min':rng.randint(6,9)},
            'maternal_context':{'gbs_status':'positive' if family=='well_single_risk' else 'unknown','rom_hours':None,
                'maternal_temperature_c':None,'intrapartum_antibiotics_adequate':None,
                'preterm_birth_indication':'maternal preeclampsia, without labor or membrane rupture' if preterm and variant%2==0 else 'preterm labor with membrane rupture' if preterm else None},
            'observations':observations,'clinical_state':{'symptoms':symptoms,'symptoms_explicitly_assessed':True,
                'culture_status':culture_status,'culture_collected_at':culture_collected,'culture_result_available_at':culture_available,
                'antibiotics_started_at':antibiotic_started,'initial_suspicion':initial_suspicion,
                'hospitalized_within_prior_14_days':True if family=='referral_constraints' and variant==5 else None,
                'beta_lactam_allergy':{'reaction':'immediate severe reaction','confirmed':True} if family=='severe_beta_lactam_allergy' else {'reaction':None,'confirmed':None}},
            'outcome':{'culture_confirmed_eos':None,'outcome_adjudicated':False},
            'expected_behaviors':expected,'gold_evidence_status':'No new gold invented; independent source mapping/adjudication required',
            'reference_care_plan':None,'not_for_model_training':True}
        cases.append(case)
    for c in cases:
        times=[datetime.fromisoformat(o['observed_at']) for o in c['observations']]
        assert len(set(times))==3 and times==sorted(times)
        end=datetime.fromisoformat(c['assessment_time']);birth=datetime.fromisoformat(c['birth_time'])
        assert 0<=(end-birth).total_seconds()/3600<72
        for o in c['observations']:
            assert datetime.fromisoformat(o['available_at'])<=end
            assert abs((datetime.fromisoformat(o['observed_at'])-birth).total_seconds()/3600-o['age_hours'])<1e-8
    OUT.mkdir(parents=True,exist_ok=True)
    payload={'version':'synthetic-eos-development-v2','seed':20261025,'cases':cases,'measurement_units':UNITS,
        'provenance':'New engineering-authored cases; original pilot cases/gold untouched. This does not correct or establish the clinical training CSV provenance.',
        'sources':SOURCES,'independence':'100 variants from 10 template families; split/evaluate by family; these are dependent development inputs.',
        'clinical_status':'Plausibility-oriented engineering cases, not clinician-adjudicated cases, EOS outcomes or a clinical training/validation cohort.'}
    path=OUT/'cases.json';path.write_text(json.dumps(payload,indent=2)+'\n')
    (OUT/'integrity.json').write_text(json.dumps({'cases':100,'observations':300,'families':10,
        'unique_case_ids':len({c['case_id'] for c in cases}),'duplicate_case_observation_ids':0,
        'age_hours_below_72':True,'future_result_leakage':False,'immutable_demographics':True,
        'invented_outcome_labels':False,'original_gold_modified':False,
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},indent=2)+'\n')
    print(json.dumps({'cases':len(cases),'families':10,'saved':str(path)}))

if __name__=='__main__':main()
