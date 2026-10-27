"""New development version: source-derived NICE headings and EOS exclusions.

No benchmark text, gold IDs or references change. A source-only annotation
excludes explicitly late-only NICE passages. Engineering scope extraction is
auditable and is NOT a substitute for clinical source review.
"""
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'output/research/expanded100'
OUT=ROOT/'output/research/rag_improvement_v2'


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')


def headings(pdf):
    import fitz
    sections={};major='';current=None
    with fitz.open(pdf) as doc:
        for page in doc:
            for block in page.get_text('dict')['blocks']:
                if 'lines' not in block:continue
                text=' '.join(' '.join(s['text'] for s in line['spans']) for line in block['lines'])
                text=' '.join(text.split()).replace('- ','-')
                size=max(s['size'] for line in block['lines'] for s in line['spans'])
                if size>=24:
                    major=text
                elif size>=20:
                    match=re.match(r'^1\.(\d+)\s+(.+)',text)
                    if match:
                        current=match.group(1)
                        sections[current]={'parent_heading':major,'section_heading':match.group(2),'pdf_page':page.number+1}
    return sections


def main():
    if (OUT/'inputs/corpus.json').exists():
        raise SystemExit('Scoped study already prepared; refusing to overwrite')
    corpus=json.loads((OLD/'corpus.json').read_text())
    cases=json.loads((OLD/'cases.json').read_text())
    pdf=ROOT/'backend/guidelines/nice_ng195_neonatal_infection_2026.pdf-8-98.pdf'
    titles=headings(pdf);included=[];excluded=[]
    for original in corpus['chunks']:
        c=copy.deepcopy(original)
        m=re.match(r'NICE-1\.(\d+)\.',c['chunk_id'])
        meta=titles.get(m.group(1),{}) if m else {}
        parent=meta.get('parent_heading','').lower()
        raw=c['text'];low=raw.lower().replace('- ','-')
        late_parent='late-onset' in parent and 'early-onset' not in parent
        late_text='late-onset' in low and 'early-onset' not in low
        if c['guideline_id']=='NICE' and (late_parent or late_text):
            excluded.append({'chunk_id':c['chunk_id'],'reason':'Explicit late-only source heading or recommendation',**meta})
            continue
        c['raw_text']=raw
        c['retrieval_headings']=meta
        c['text']=' / '.join([s for s in [meta.get('parent_heading'),meta.get('section_heading'),raw] if s])
        c['index_text_sha256']=hashlib.sha256(c['text'].encode()).hexdigest()
        included.append(c)
    ids={c['chunk_id'] for c in included}
    missing={g for c in cases for g in c['gold_chunk_ids'] if g not in ids}
    if missing:raise ValueError(f'Scope conflicts with existing gold: {sorted(missing)}. Clinician adjudication required; do not silently change labels.')
    (OUT/'inputs').mkdir(parents=True,exist_ok=True)
    (OUT/'inputs/cases.json').write_bytes((OLD/'cases.json').read_bytes())
    (OUT/'inputs/retrieval.json').write_bytes((OLD/'retrieval.json').read_bytes())
    save(OUT/'inputs/corpus.json',{**corpus,'chunks':included,'purpose':'development-only source-heading index; raw_text is the immutable generation evidence'})
    save(OUT/'scope_audit.json',{'sections':titles,'excluded':excluded,'included':len(included),
         'original_corpus_sha256':hashlib.sha256((OLD/'corpus.json').read_bytes()).hexdigest(),
         'source_pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
         'case_file_unchanged':(OUT/'inputs/cases.json').read_bytes()==(OLD/'cases.json').read_bytes(),
         'gold_ids_missing':sorted(missing),'clinical_review':'pending'})
    print('Included',len(included),'excluded',len(excluded),'all gold IDs retained',not missing)


if __name__=='__main__':main()
