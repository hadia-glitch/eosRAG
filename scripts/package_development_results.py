"""Package intended research inputs/results, excluding task scratch and caches."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'output/research'


def main():
    files=[]
    excluded={'role_cache','judge_cache','score_cache','embedding_cache','__pycache__','qa','intermediates'}
    for name in ['rag_improvement_v1','rag_improvement_v2','rag_improvement_v3','rag_improvement_v4','rag_development']:
        for p in sorted((DATA/name).rglob('*')):
            if not p.is_file() or excluded&set(p.parts):continue
            if p.name.startswith('pending_') or p.name=='clinician_panel_key.json':continue
            if p.suffix not in {'.json','.csv','.md','.xml'}:continue
            files.append(p)
    for name in ['cases.json','manifest.json','protocol.json','corpus.json','benchmark_report.md']:
        files.append(DATA/'expanded100'/name)
    files.extend([ROOT/'docs/research/final_evaluation_gate.md',ROOT/'docs/research/rag_development_report.md',
                  ROOT/'docs/research/rag_remaining_gaps.md',
                  ROOT/'docs/research/evaluated_pipeline_app_handoff.md',
                  ROOT/'docs/research/manuscript.md',ROOT/'output/pdf/neoguard-eos-research-paper.pdf'])
    manifest={'stage':'development_only','final_evaluation':'on hold','synthetic_cases':100,
        'real_patient_data_included':False,'clinical_validation':'not performed',
        'operational_and_provider_failure_logs':'excluded from quality results; retained locally',
        'files_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    target=DATA/'rag_development/results_manifest.json'
    files=[p for p in files if p!=target]
    manifest['files_sha256'].pop(str(target.relative_to(ROOT)).replace('\\','/'),None)
    target.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    files.append(target)
    archive=DATA/'neoguard-rag-development-results.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,str(p.relative_to(ROOT)).replace('\\','/'))
    print(json.dumps({'archive':str(archive),'files':len(files),'bytes':archive.stat().st_size,
                     'final_evaluation':'on hold'}))


if __name__=='__main__':main()
