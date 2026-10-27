from services.plan_sections import build_sections

def test_thirteen_sections_preserve_missing_evidence_and_patient_privacy():
    claims=[{'section':'monitoring_plan','text':'Record observations during assessment.',
             'support':[{'evidence_id':'E1'}]}]
    sections=build_sections({'age_hours':6,'name':'private fixture name'},'Two recorded assessments.',claims,True)
    assert [s['id'] for s in sections]==[f'S{i:02d}' for i in range(1,14)]
    assert 'private fixture name' not in str(sections)
    assert sections[8]['status']=='evidence_supported'
    assert sections[8]['evidence_labels']==['E1']
    assert sections[6]['status']=='not_determined' and sections[6]['evidence_labels']==[]
    withheld=build_sections({'age_hours':6},'Two recorded assessments.',claims,False)
    assert not any(s['status']=='evidence_supported' for s in withheld)
    assert 'Record observations during assessment.' not in str(withheld)
