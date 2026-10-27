"""Auditable PDF headings for retrieval, without granting clinical approval."""
import re


def nice_headings(pdf):
    import fitz
    sections={};major=''
    with fitz.open(pdf) as doc:
        for page in doc:
            for block in page.get_text('dict')['blocks']:
                if 'lines' not in block:continue
                text=' '.join(' '.join(s['text'] for s in line['spans']) for line in block['lines'])
                text=' '.join(text.split()).replace('- ','-')
                size=max(s['size'] for line in block['lines'] for s in line['spans'])
                if size>=24:major=text
                elif size>=20:
                    m=re.match(r'^1\.(\d+)\s+(.+)',text)
                    if m:sections[m.group(1)]={'parent_heading':major,'section_heading':m.group(2),'pdf_page':page.number+1}
    return sections


def late_only(text,parent=''):
    parent=parent.lower().replace('- ','-')
    text=text.lower().replace('- ','-')
    return (('late-onset' in parent and 'early-onset' not in parent)
            or ('late-onset' in text and 'early-onset' not in text))


def retrieval_text(row):
    meta=row.get('metadata') or {}
    return ' / '.join(s for s in [meta.get('retrieval_parent_heading'),meta.get('retrieval_section_heading'),row['chunk_text']] if s)
