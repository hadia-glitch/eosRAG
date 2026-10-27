"""Index eligible experiment populations separately from operational attempts."""
import json
from pathlib import Path
from scripts.evaluation_transport import quality_eligible

ROOT=Path(__file__).resolve().parents[2]

if __name__=='__main__':
    quality={};operational={}
    for name in ['rag','rag_v2']:
        folder=ROOT/'output/operational/quote_echo/runs' if name=='rag' else ROOT/f'output/research/{name}/runs'
        records=[json.loads(p.read_text()) for p in sorted(folder.glob('*.json'))]
        eligible=[r for r in records if quality_eligible(r)]
        quality[name]={'planned_n':len(records),'n':len(eligible),'eligible_case_ids':[r['id'] for r in eligible],
                       'generated':sum(bool(r['result'].get('draft')) for r in eligible),
                       'released':sum(r['result']['status']=='supported_for_review' for r in eligible)}
        operational[name]={'provider_incomplete_case_ids':[r['id'] for r in records if not quality_eligible(r)]}
    (ROOT/'output/research/quality_population.json').write_text(json.dumps(quality,indent=2)+'\n')
    path=ROOT/'output/operational/quality_population_exclusions.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(operational,indent=2)+'\n')
    print({k:{field:v[field] for field in ['n','generated','released']} for k,v in quality.items()})
