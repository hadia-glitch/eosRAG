"""Add the latest blinded synthetic evidence panels; never include PIC records."""
import csv,hashlib,html,json,random,zipfile
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'output/research/rag_development'
OUT=ROOT/'output/clinician-review/neoguard-development-review'


def csv_file(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    if not (OUT/'manifest.json').exists():raise ValueError('Build the original development review pack first')
    cases=json.loads((ROOT/'output/research/expanded100/cases.json').read_text())
    corpus={c['chunk_id']:c for c in json.loads((DATA/'recommendation_units/corpus.json').read_text())['chunks']}
    graph=json.loads((DATA/'structured_context/workflow_context_graph.json').read_text())
    definitions={n['chunk_id']:n for n in json.loads((DATA/'definition_context_graph.json').read_text())['nodes']}
    rng=random.Random(31);esc=html.escape;ratings=[];articles=[];keys=[]
    for case in cases:
        path=DATA/'structured_context/runs'/f'{case["id"]}.json'
        record=json.loads(path.read_text());choices=list(record['rankings'].items());rng.shuffle(choices)
        panels=[]
        for panel,(method,rankings) in zip(['A','B','C'],choices):
            keys.append({'study':'source_context_100','id':case['id'],'panel':panel,'method':method})
            ratings.append({'id':case['id'],'guideline':record['guideline'],'panel':panel,
                'directly_relevant_passages_0_to_4':'','essential_evidence_omitted_yes_no_uncertain':'',
                'wrong_population_setting_or_timing_yes_no_uncertain':'','source_conditions_complete_yes_no_uncertain':'',
                'observed_history_used_appropriately_yes_no_uncertain':'','useful_for_question_1_to_5':'',
                'reviewer_code':'','review_date':'','notes':''})
            snippets=[];extra=set()
            for position,cid in enumerate(rankings['4'],1):
                c=corpus[cid]
                snippets.append(f'<section><b>{position}. {esc(cid)}</b><p>{esc(c["raw_text"])}</p>'
                    f'<small>{esc(c["source"])} · supplied PDF page(s) {esc(str(c.get("pdf_pages",[c["pdf_page"]])))} '
                    f'· source text SHA256 {esc(c["text_sha256"])}</small></section>')
                extra.update(record['definition_context_ids'][cid])
            for cid in sorted(extra):
                c=definitions[cid]
                snippets.append(f'<aside><b>Supplemental publisher definition (outside top-four slots)</b><p>{esc(c["raw_text"])}</p>'
                    f'<small>{esc(cid)} · source text SHA256 {esc(c["text_sha256"])}</small></aside>')
            panels.append(f'<div class="panel"><h3>Panel {panel}</h3>{"".join(snippets)}</div>')
        articles.append(f'<details><summary>{esc(case["id"])} · {esc(record["guideline"])}</summary>'
            f'<h2>{esc(case["query"])}</h2><h3>Recorded current findings</h3><pre>{esc(json.dumps(case["patient"],indent=2))}</pre>'
            f'<h3>Recorded history</h3><pre>{esc(json.dumps(case["history"],indent=2))}</pre><div class="panels">{"".join(panels)}</div></details>')
    csv_file('source_context_panel_ratings.csv',ratings)
    (OUT/'source_context_cases.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Latest source-context review</title>'
        '<style>body{font:16px/1.6 system-ui;max-width:1500px;margin:auto;padding:24px;color:#17324d}'
        'details{border:1px solid #b9cbd5;padding:16px;margin:16px 0}summary{font-weight:bold;cursor:pointer}'
        '.panels{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}'
        'section,aside{background:#f1f7f8;border-left:4px solid #087f8c;padding:12px;margin:12px 0}'
        'aside{background:#fff4db}p,pre{white-space:pre-wrap}</style><h1>Latest source-context development review</h1>'
        '<p>100 unchanged synthetic cases; three shuffled source-evidence panels per case. Source/graph labels and '
        'clinical relevance remain unapproved. These are evidence sets, not treatment plans. Inspect all '
        'conditions, unseen alternatives and whether recorded history is used appropriately. Do not infer '
        'that a retrieved rule establishes patient eligibility. Review ratings are blank.</p>'
        +''.join(articles)+'</html>',encoding='utf8')
    csv_file('source_context_edge_review.csv',[{'source_chunk':e['from'],'target_chunk':e['to'],'proposed_relation':e['relation'],
        'source_text':corpus[e['from']]['raw_text'],'target_text':corpus[e['to']]['raw_text'],
        'same_document_verified':corpus[e['from']]['pdf_sha256']==corpus[e['to']]['pdf_sha256'],
        'context_relation_valid_yes_no_uncertain':'','clinically_misleading_use_yes_no_uncertain':'',
        'reviewer_code':'','review_date':'','notes':''} for e in graph['edges']])
    audit=json.loads((DATA/'structured_context/source_topic_audit.json').read_text());seen=set();exclusions=[]
    for r in audit:
        key=(r['chunk_id'],r['reason'])
        if key in seen:continue
        seen.add(key);c=corpus[r['chunk_id']]
        exclusions.append({'example_case':r['id'],'chunk_id':r['chunk_id'],'proposed_exclusion':r['reason'],
            'text':c['raw_text'],'exclusion_appropriate_yes_no_uncertain':'','would_remove_useful_conditional_evidence':'','reviewer_code':'','notes':''})
    if exclusions:csv_file('source_context_exclusion_review.csv',exclusions)
    queue=DATA/'structured_context/failure_review_queue.csv'
    if queue.exists():shutil.copy2(queue,OUT/'source_context_failure_review_queue.csv')
    key_path=DATA/'clinician_panel_key.json';old=json.loads(key_path.read_text())
    key_path.write_text(json.dumps([r for r in old if r['study']!='source_context_100']+keys,indent=2)+'\n')
    note='''

## Latest addendum: source-context development

Open source_context_cases.html first for the latest candidate. Complete the 300 blank rows in source_context_panel_ratings.csv. The three evidence panels are shuffled separately for each of the 100 unchanged synthetic cases; no method key is included. Some panels are identical, reflecting a genuine null ablation.

Review source_context_edge_review.csv and source_context_exclusion_review.csv for clinically misleading relationships or excluded useful conditional evidence. Graph edges are engineering links, not clinically approved causal relations. Publisher definitions are explicitly labelled as supplemental context outside the top-four recommendation slots. High engineering recall does not approve the relevance labels or patient applicability.

The real-data PIC longitudinal comparison is not ready for clinical prediction: 543 infants but only seven independent documented-pathogen outcomes under the strict pre-culture cohort. No real PIC patient rows, model weights, individual predictions or inferred maternal histories are included. A linked obstetric-neonatal cohort and outcome adjudication are required before combined clinical prediction.
'''
    readme=OUT/'README.md';text=readme.read_text();marker='\n\n## Latest addendum: source-context development'
    if marker in text:text=text.split(marker)[0]
    readme.write_text(text+note,encoding='utf8')
    manifest=json.loads((OUT/'manifest.json').read_text());manifest.update(source_context_cases=100,source_context_panel_rows=len(ratings),
        source_context_edge_rows=len(graph['edges']),real_patient_data_included=False)
    manifest['files_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=OUT.parent/'neoguard-development-clinician-review.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()):
            if p.is_file():z.write(p,p.name)
    print(json.dumps({'archive':str(archive),'new_case_panels':len(ratings),'raw_pic_data_included':False,'clinical_review':'not performed'}))


if __name__=='__main__':main()
