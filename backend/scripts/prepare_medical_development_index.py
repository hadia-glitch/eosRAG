"""Source-only hierarchy repair for the development index; golds unchanged."""
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/research/rag_development/medcpt'


def layout_map(path,source):
    import fitz
    by_block={};by_section={};major='';section='';section_id=''
    with fitz.open(path) as doc:
        for page in doc:
            for i,block in enumerate(page.get_text('dict')['blocks']):
                if 'lines' not in block:continue
                text=' '.join(' '.join(s['text'] for s in l['spans']) for l in block['lines'])
                text=' '.join(text.split()).replace('- ','-')
                size=max(s['size'] for l in block['lines'] for s in l['spans'])
                if source=='WHO':
                    if 24<=size<=30:
                        major=text
                        if not re.match(r'^[AB]\.',text):section_id='';section=''
                    m=re.match(r'^([AB]\.\d+)\s+(.+)',text)
                    if 15<=size<=20 and m:
                        section_id=m[1];section=m[2]
                        by_section[section_id]={'parent_heading':major,'section_heading':section,'section_id':section_id}
                elif 9.95<=size<=10.3 and 5<len(text)<220:
                    if text.upper()==text:major=text
                    section=text
                by_block[(page.number+1,i)]={'parent_heading':major,'section_heading':section,
                    'section_id':section_id,'raw_block':' '.join(text.split())}
    return by_block,by_section


def main():
    target=OUT/'corpus.json'
    if target.exists():raise SystemExit('Development index already prepared; refusing overwrite')
    prior=ROOT/'output/research/rag_improvement_v2/inputs'
    data=json.loads((prior/'corpus.json').read_text())
    who=next((ROOT/'backend/guidelines').glob('WHO*.pdf'))
    aap=ROOT/'backend/guidelines/aap_management_of_neonates-1-7 (1).pdf'
    mappings={'WHO':layout_map(who,'WHO'),'AAP':layout_map(aap,'AAP')}
    audit=[]
    for c in data['chunks']:
        raw=c.get('raw_text',c['text']);meta=c.get('retrieval_headings',{})
        source=c['guideline_id']
        if source in mappings:
            blocks,sections=mappings[source]
            match=re.search(r'-P(\d+)-B(\d+)$',c['chunk_id'])
            if match:meta=blocks.get((int(match[1]),int(match[2])),{})
            elif source=='WHO':
                m=re.match(r'WHO2024-([AB]\.\d+)',c['chunk_id'])
                meta=sections.get(m[1],{}) if m else {}
            if not meta:
                candidates=[v for (page,_),v in blocks.items() if page==c['pdf_page'] and ' '.join(raw.split())[:70] in v['raw_block']]
                if candidates:meta=candidates[0]
            if source=='AAP' and '-SP' in c['chunk_id']:
                choices=[v for v in blocks.values() if 'SUMMARY POINTS' in v['section_heading']]
                if choices:meta=choices[-1]
            meta={k:v for k,v in meta.items() if k!='raw_block'}
            c['retrieval_headings']=meta
            sid=meta.get('section_id','')
            if source=='WHO' and sid:
                c['scope']['care_setting']=['non_hospital'] if sid.startswith('A.') else ['hospital']
                c['scope']['postnatal_age_hours']=[168,1439] if sid=='A.5' else [0,167] if sid=='A.4' else [0,1439]
        c['raw_text']=raw
        c['text']=' / '.join(s for s in [meta.get('parent_heading'),meta.get('section_heading'),raw] if s)
        c['index_text_sha256']=hashlib.sha256(c['text'].encode()).hexdigest()
        audit.append({'chunk_id':c['chunk_id'],'headings':meta,'scope':c['scope'],'clinical_review':'pending'})
    OUT.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
    (OUT/'source_structure_audit.json').write_text(json.dumps({'chunks':audit,'scope_review':'engineering extraction; clinician review pending',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [who,aap]}},indent=2)+'\n')
    print('Development chunks:',len(data['chunks']))


if __name__=='__main__':main()
