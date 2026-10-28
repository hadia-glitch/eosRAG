"""NICE recommendation and box boundaries in footer-stripped PDF text.

Pure structural extraction; no clinical approval or semantic rewriting. Offsets
refer to the declared extracted text stream, not binary PDF byte coordinates.
"""
import hashlib
import re

ANCHOR = re.compile(r'(?m)^(?:(?P<rec>1\.\d+\.\d+)\s*\n|Box (?P<box>\d+):)')
TRAILING = re.compile(r'(?m)^1\.\d+\s+[^\n]|For a short explanation|Full details of the evidence')


def extract_nice_units(pages):
    stream = '\n'.join(pages)
    anchors = list(ANCHOR.finditer(stream))
    offsets = []
    position = 0
    for page in pages:
        offsets.append((position, position + len(page)))
        position += len(page) + 1
    stream_hash = hashlib.sha256(stream.encode()).hexdigest()
    units = {}
    for i, match in enumerate(anchors):
        cid = 'NICE-' + (match['rec'] if match['rec'] else 'box' + match['box'])
        if cid in units:
            continue
        start = match.end() if match['rec'] else match.start()
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(stream)
        stop = TRAILING.search(stream, start, end)
        if stop:
            end = stop.start()
        while start < end and stream[start].isspace():
            start += 1
        while end > start and stream[end - 1].isspace():
            end -= 1
        if end <= start:
            raise ValueError('Empty recommendation unit: ' + cid)
        raw = stream[start:end]
        units[cid] = {'raw_text': ' '.join(raw.split()),
                      'source_span': {'coordinate_system': 'joined_footer_stripped_PyMuPDF_text',
                                      'stream_sha256': stream_hash, 'start': start, 'end': end,
                                      'extracted_span_sha256': hashlib.sha256(raw.encode()).hexdigest()},
                      'pdf_pages': [j + 1 for j, (a, b) in enumerate(offsets) if a < end and b > start]}
    return units, stream
