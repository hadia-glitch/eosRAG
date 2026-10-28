"""Versioned source-boundary correction; existing cases and gold IDs stay fixed."""
import hashlib
import json
import sys
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from rag.recommendation_units import extract_nice_units
from scripts.evaluate_rag_improvements import save

OUT = ROOT / 'output/research/rag_development/recommendation_units'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    original = ROOT / 'output/research/rag_development/medcpt/corpus.json'
    pdf = ROOT / 'backend/guidelines/nice_ng195_neonatal_infection_2026.pdf-8-98.pdf'
    old = json.loads(original.read_text())
    with fitz.open(pdf) as doc:
        pages = [p.get_text().split('Neonatal infection: antibiotics for prevention')[0].replace('\u00a0', ' ') for p in doc]
    units, stream = extract_nice_units(pages)
    changed, chunks = [], []
    for c in old['chunks']:
        if c['guideline_id'] != 'NICE':
            chunks.append(c)
            continue
        if c['chunk_id'] not in units:
            raise ValueError('Existing passage lacks source unit: ' + c['chunk_id'])
        unit = units[c['chunk_id']]
        text = unit['raw_text']
        if text != c['raw_text']:
            changed.append({'chunk_id': c['chunk_id'], 'old_text': c['raw_text'], 'new_text': text,
                            'old_text_sha256': hashlib.sha256(c['raw_text'].encode()).hexdigest(),
                            'new_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                            'pdf_pages': unit['pdf_pages'], 'source_span': unit['source_span']})
        headings = c.get('retrieval_headings', {})
        title = ' / '.join(s for s in [headings.get('parent_heading'), headings.get('section_heading')] if s)
        index_text = title + ' / ' + text if title else text
        chunks.append({**c, 'raw_text': text, 'text': index_text,
                       'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                       'index_text_sha256': hashlib.sha256(index_text.encode()).hexdigest(),
                       'pdf_page': unit['pdf_pages'][0], 'pdf_pages': unit['pdf_pages'],
                       'source_span': unit['source_span'], 'clinical_review_status': 'pending'})
    by_id = {c['chunk_id']: c for c in chunks}
    cases_file = ROOT / 'output/research/expanded100/cases.json'
    cases = json.loads(cases_file.read_text())
    for c in cases:
        for cid in c['gold_chunk_ids']:
            if cid not in by_id:
                raise ValueError('Missing gold ID after corpus repair: ' + cid)
    if 'altered glucose homeostasis' not in by_id['NICE-box2']['raw_text'] or 'metabolic acidosis' not in by_id['NICE-box2']['raw_text']:
        raise ValueError('Cross-page Box 2 remains incomplete')
    if 'Box 2:' in by_id['NICE-1.10.2']['raw_text'] or 'Box 1:' in by_id['NICE-1.9.2']['raw_text']:
        raise ValueError('Box contamination remains')
    protocol = {'stage': 'development_only', 'final_evaluation': False,
                'change': 'Source boundaries only: separate boxes, carry cross-page box continuations and remove trailing section headings. No gold changes or clinical review asserted.',
                'cases_sha256': sha(cases_file), 'parent_corpus_sha256': sha(original),
                'source_pdf_sha256': sha(pdf), 'extractor': 'PyMuPDF ' + fitz.VersionBind,
                'code_sha256': {p: sha(ROOT / p) for p in ['backend/rag/recommendation_units.py', 'backend/scripts/prepare_recommendation_corpus.py']},
                'source_text_stream_sha256': hashlib.sha256(stream.encode()).hexdigest(),
                'chunks': len(chunks), 'changed_chunks': len(changed), 'gold_ids_missing': 0,
                'clinical_review_status': 'pending'}
    target = OUT / 'corpus_protocol.json'
    if target.exists() and json.loads(target.read_text()) != protocol:
        raise ValueError('Recommendation-corpus protocol drift')
    save(target, protocol)
    save(OUT / 'corpus.json', {'chunks': chunks, 'source_pdf_sha256': sha(pdf), 'clinical_review_status': 'pending'})
    save(OUT / 'source_boundary_changes.json', changed)
    save(OUT / 'source_span_audit.json', {'source_pdf_sha256': sha(pdf), 'changed': len(changed),
         'all_nice_spans_round_trip': all(' '.join(stream[u['source_span']['start']:u['source_span']['end']].split()) == u['raw_text'] for u in units.values()),
         'box2_pages': by_id['NICE-box2']['pdf_pages'], 'cases_unchanged_sha256': sha(cases_file)})
    print(json.dumps(protocol, indent=2))


if __name__ == '__main__':
    main()
