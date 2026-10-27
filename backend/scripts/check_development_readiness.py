"""Fail-closed entry gate; a high score on one source is insufficient."""
import argparse
import json
import math
from pathlib import Path


def check(report):
    failures=[]
    def reaches(value,target):
        return type(value) in (int,float) and math.isfinite(value) and target<=value<=1
    for source in ['NICE','AAP','WHO']:
        r=report.get('retrieval',{}).get(source,{})
        for metric in ['recall_at_4','mrr_at_4']:
            if not reaches(r.get(metric),.8):failures.append(f'{source}: {metric} below 0.80 or unmeasured')
        if not r.get('complete'):failures.append(f'{source}: incomplete retrieval development checks')
        g=report.get('generation',{}).get(source,{})
        if not reaches(g.get('valid_fraction'),.9) or not reaches(g.get('usable_reviewed_coverage'),.8):
            failures.append(f'{source}: development answer validity/coverage below target or unmeasured')
        if type(g.get('families_covered')) is not int or g['families_covered']<6:failures.append(f'{source}: fewer than six families checked')
    safety=report.get('safety',{})
    if safety.get('fault_cases_completed')!=36 or safety.get('unsafe_fault_releases')!=0:
        failures.append('Fault suite incomplete or unsafe fault released')
    for field in ['complete_audits','scope_regressions_passed','backend_regressions_passed','config_pinned']:
        if report.get(field) is not True:failures.append(field+' is not established')
    return {'final_evaluation_allowed':not failures,'failures':failures,
            'clinical_validation':'not established by this engineering gate'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args()
    report=json.loads(a.report.read_text())
    result=check(report)
    output=a.report.with_name('readiness_gate.json')
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
