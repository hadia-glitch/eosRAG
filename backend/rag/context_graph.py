"""Typed, source-derived context edges; graph edges are not medical claims.

Definition text is an exact complete sentence from the same publisher section.
No language model, benchmark labels or inferred clinical relationships are used.
These nodes supplement selected evidence; they never silently replace a top-k
slot or establish that an infant satisfies a definition.
"""
import hashlib
import re
from rag.clinical_scope import applicable


def definition_spans(text):
    # A decimal point cannot terminate a sentence here. Requiring a terminal
    # punctuation mark avoids admitting PDF fragments cut off at a page end.
    pattern=r'[^.!?]*\b(?:is|are) defined (?:as|by)\b.*?(?:[.!?](?=\s+[A-Z]|$))'
    for match in re.finditer(pattern,text,re.S|re.I):
        value=match.group(0)
        # Recheck the last punctuation separately from case-insensitive matching.
        if value[-1:] not in '.!?':continue
        start=match.start()
        prefix=re.match(r'\s*Background and definitions\s+',value,re.I)
        if prefix:start+=prefix.end();value=value[prefix.end():]
        yield {'start':start,'end':match.end(),'text':value}


def build_context_graph(chunks):
    nodes={};edges=[];sections={}
    for c in chunks:
        heading=c.get('retrieval_headings') or {}
        section=heading.get('section_id')
        if not section:continue
        key=(c['guideline_id'],c['pdf_sha256'],section)
        sections.setdefault(key,[]).append(c)
        for span in definition_spans(c['raw_text']):
            digest=hashlib.sha256(span['text'].encode()).hexdigest()
            node_id=c['chunk_id']+'::definition:'+digest[:12]
            nodes[node_id]={**c,'chunk_id':node_id,'raw_text':span['text'],'text':span['text'],
                'text_sha256':digest,'parent_chunk_id':c['chunk_id'],
                'source_span':{'start':span['start'],'end':span['end']},
                'graph_role':'publisher_definition','clinical_review_status':'pending'}
    for node_id,node in nodes.items():
        h=node['retrieval_headings'];key=(node['guideline_id'],node['pdf_sha256'],h['section_id'])
        for c in sections[key]:
            if c.get('chunk_type')=='recommendation_and_qualifiers':
                edges.append({'from':c['chunk_id'],'to':node_id,'relation':'HAS_SECTION_DEFINITION',
                    'source_pdf_sha256':node['pdf_sha256'],'section_id':h['section_id'],
                    'clinical_review_status':'pending'})
    return {'nodes':list(nodes.values()),'edges':edges,'method':'publisher section membership and exact definition sentences'}


def context_for(selected_ids,graph,patient,*,max_nodes=4):
    if type(max_nodes) is not int or not 0<=max_nodes<=8:raise ValueError('Invalid graph context budget')
    nodes={n['chunk_id']:n for n in graph['nodes']};selected=set(selected_ids);out=[]
    seen={n['text_sha256'] for n in nodes.values() if n.get('parent_chunk_id') in selected}
    for edge in graph['edges']:
        if edge['from'] not in selected:continue
        node=nodes[edge['to']]
        if node['text_sha256'] in seen or not applicable(node['scope'],patient):continue
        # Exact text already selected as a full definition need not be repeated.
        if node.get('parent_chunk_id') in selected:continue
        out.append(node);seen.add(node['text_sha256'])
        if len(out)>=max_nodes:break
    return out if max_nodes else []
