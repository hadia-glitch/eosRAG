"""Package measured study data and tables; excludes operational/API-availability logs."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'output/research/expanded100'

def main():
    summary=json.loads((DATA/'tables_summary.json').read_text())
    integrity=json.loads((DATA/'integrity_report.json').read_text())
    if not summary.get('overall_complete') or not integrity.get('all_declared_work_complete'):
        raise SystemExit('Declared study incomplete; final results archive refused')
    if not (DATA/'paper_revision/sentence_changes.csv').exists():
        raise SystemExit('Final paper change log missing')
    selected=[]
    for path in sorted(DATA.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(DATA)
        if any(p in {'qa','role_cache','judge_cache','intermediates'} for p in rel.parts):continue
        if path.name=='pending_transport.json':continue
        if path.suffix not in {'.json','.csv','.md'}:continue
        selected.append((path,Path('study')/rel))
    for rel in ['docs/research/expanded100_protocol.md','docs/research/manuscript.md']:
        path=ROOT/rel
        selected.append((path,Path(rel)))
    selected.append((ROOT/'output/pdf/neoguard-eos-research-paper.pdf',Path('paper/neoguard-eos-research-paper.pdf')))
    names=[str(name).replace('\\','/') for _,name in selected]
    assert len(names)==len(set(names))
    hashes={name:hashlib.sha256(path.read_bytes()).hexdigest() for (path,_),name in zip(selected,names)}
    description=('NeoGuard: completed 100-case synthetic EOS study\n\n'
        'NICE 40; AAP 30; WHO 30. The original 18 vignettes are unchanged.\n'
        'This archive contains all CSV tables, the synthetic dataset/reference\n'
        'passages, measured raw role outcomes, protocols, hashes, environment\n'
        'versions, integrity checks and final sentence/number change logs.\n'
        'API-availability logs and duplicate role caches are excluded.\n'
        'Source PDFs, real patient tables, credentials and demo files are excluded.\n'
        'Guideline text remains attributed to its original publisher.\n\n'
        'Use the eosRAG repository and docs/research/expanded100_protocol.md for\n'
        'reproduction; model aliases are not immutable provider snapshots.\n'
        'These are engineering measurements and not clinical validation.\n')
    target=ROOT/'output/research/neoguard-expanded100-results.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path,name in selected:
            archive.write(path,'neoguard-expanded100-results/'+str(name).replace('\\','/'))
        archive.writestr('neoguard-expanded100-results/README.txt',description)
        archive.writestr('neoguard-expanded100-results/bundle_hashes.json',json.dumps(hashes,indent=2)+'\n')
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert not any('/role_cache/' in n or n.endswith('/.env') or '/operational/' in n for n in archive.namelist())
    print({'archive':str(target),'files':len(selected),'bytes':target.stat().st_size,
           'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})

if __name__=='__main__':
    main()
