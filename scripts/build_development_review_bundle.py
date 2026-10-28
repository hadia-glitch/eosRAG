"""Prepare an uncompleted clinician review pack from development evidence."""
import csv
import hashlib
import html
import json
import random
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'output/research'
OUT=ROOT/'output/clinician-review/neoguard-development-review'


def write_csv(path,rows):
    if not rows:return
    with path.open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    corpus={c['chunk_id']:c for c in json.loads((DATA/'rag_development/medcpt/corpus.json').read_text())['chunks']}
    cases=json.loads((DATA/'expanded100/cases.json').read_text())
    records={p.stem:json.loads(p.read_text()) for p in (DATA/'rag_development/listwise/runs').glob('*.json')}
    consensus={p.stem:json.loads(p.read_text()) for p in (DATA/'rag_development/consensus/runs').glob('*.json')}
    if len(records)!=100:raise ValueError('Incomplete development selection: no finished review pack emitted')
    if len(consensus)!=100:raise ValueError('Incomplete consensus development')
    OUT.mkdir(parents=True,exist_ok=True);rng=random.Random(31)
    ratings=[];relevance=[];scope=[];key=[];priority=[];articles=[]
    esc=html.escape
    urls={'NICE':'https://www.nice.org.uk/guidance/ng195',
          'AAP':'https://doi.org/10.1542/peds.2018-2894',
          'WHO':'https://www.who.int/publications/i/item/9789240102903'}
    for case in cases:
        r=records[case['id']];gold=set(case['gold_chunk_ids']);selected=consensus[case['id']]['rankings']['4']
        missed=sorted(gold-set(selected))
        priority.append({'id':case['id'],'guideline':r['guideline'],'family':case['family'],
            'engineering_gold_missed_at_4':len(missed),'missing_proposed_gold':'|'.join(missed),
            'review_reason':'Proposed relevance is uncertain; compare whole clinical question and full source conditions.',
            'clinician_priority':'','clinician_notes':''})
        methods=[('upstream_fusion',r['baseline_ids'][:4]),('consensus',selected)];rng.shuffle(methods)
        panels=[]
        for label,(method,ids) in zip(['A','B'],methods):
            key.append({'study':'complete_consensus','id':case['id'],'panel':label,'method':method})
            ratings.append({'id':case['id'],'guideline':r['guideline'],'panel':label,
                'directly_relevant_passages_0_to_4':'','essential_evidence_omitted_yes_no_uncertain':'',
                'wrong_population_or_setting_yes_no_uncertain':'','conditions_preserved_yes_no_uncertain':'',
                'useful_for_this_information_need_1_to_5':'','needs_urgent_correction_yes_no':'',
                'reviewer_code':'','review_date':'','notes':''})
            snippets=[]
            for rank,cid in enumerate(ids,1):
                c=corpus[cid]
                snippets.append(f'<section><b>{rank}. {esc(cid)}</b><p>{esc(c["raw_text"])}</p>'
                    f'<small>{esc(c["source"])}; supplied PDF page {c["pdf_page"]}; '
                    f'<a href="{urls[r["guideline"]]}">Publisher source</a></small></section>')
            panels.append(f'<div class="panel"><h3>Panel {label}</h3>{"".join(snippets) or "No evidence selected."}</div>')
        for cid in r['candidate_ids']:
            c=corpus[cid]
            relevance.append({'id':case['id'],'guideline':r['guideline'],'chunk_id':cid,
                'publisher_url':urls[r['guideline']],'pdf_page':c['pdf_page'],'passage_text':c['raw_text'],
                'relevance_direct_supporting_irrelevant_uncertain':'','conditions_or_definition_missing':'',
                'reviewer_code':'','notes':''})
        articles.append(f'<details id="{esc(case["id"])}"><summary>{esc(case["id"])} · {esc(r["guideline"])} · '
            f'{esc(case["family"])}</summary><h2>{esc(case["query"])}</h2>'
            f'<h3>Recorded current findings</h3><pre>{esc(json.dumps(case["patient"],indent=2))}</pre>'
            f'<h3>Recorded observation history</h3><pre>{esc(json.dumps(case.get("history",[]),indent=2))}</pre>'
            f'<div class="panels">{"".join(panels)}</div></details>')
    for c in corpus.values():
        scope.append({'chunk_id':c['chunk_id'],'guideline':c['guideline_id'],'publisher_url':urls[c['guideline_id']],
            'source_pdf_sha256':c['pdf_sha256'],'supplied_pdf_page':c['pdf_page'],
            'proposed_scope_json':json.dumps(c['scope']),'heading_json':json.dumps(c.get('retrieval_headings',{})),
            'text':c['raw_text'],'scope_correct_yes_no_uncertain':'','complete_recommendation_or_definition_yes_no_uncertain':'',
            'approved_population':'','corrected_scope_json':'','reviewed_by':'','reviewed_at':'','notes':''})
    write_csv(OUT/'panel_ratings.csv',ratings);write_csv(OUT/'passage_relevance_review.csv',relevance)
    write_csv(OUT/'source_scope_review.csv',scope)
    graph=json.loads((DATA/'rag_development/definition_context_graph.json').read_text())
    write_csv(OUT/'definition_context_review.csv',[{'definition_id':n['chunk_id'],
        'parent_passage_id':n['parent_chunk_id'],'source_pdf_sha256':n['pdf_sha256'],
        'source_span_json':json.dumps(n['source_span']),'exact_text':n['raw_text'],
        'definition_correct_and_complete_yes_no_uncertain':'','section_relation_correct_yes_no_uncertain':'',
        'reviewed_by':'','reviewed_at':'','notes':''} for n in graph['nodes']])
    write_csv(OUT/'engineering_priority_queue.csv',sorted(priority,key=lambda r:-r['engineering_gold_missed_at_4']))
    pilot_protocol=DATA/'rag_development/patient_conditioned/development_protocol.json'
    dependency_summary=DATA/'rag_development/dependencies/summary.json'
    pilot_ratings=[];pilot_articles=[];pilot_node_review=[]
    if pilot_protocol.exists() and dependency_summary.exists():
        pilot_ids=json.loads(pilot_protocol.read_text())['pilot_case_ids']
        by_id={c['id']:c for c in cases}
        seen_nodes=set()
        for cid in pilot_ids:
            case=by_id[cid];source=records[cid]['guideline']
            patient=json.loads((DATA/'rag_development/patient_conditioned/runs'/f'{cid}.json').read_text())
            dependency=json.loads((DATA/'rag_development/dependencies/runs'/f'{cid}.json').read_text())
            methods=[('question_consensus',consensus[cid]['rankings']['4']),
                     ('patient_consensus',patient['consensus_ids'][:4]),
                     ('dependency_consensus',dependency['consensus_ids'][:4])]
            rng.shuffle(methods);panels=[]
            for label,(method,ids) in zip(['A','B','C'],methods):
                key.append({'study':'balanced_pilot','id':cid,'panel':label,'method':method})
                pilot_ratings.append({'id':cid,'guideline':source,'panel':label,
                    'directly_relevant_passages_0_to_4':'','essential_evidence_omitted_yes_no_uncertain':'',
                    'wrong_population_or_timing_yes_no_uncertain':'','conditions_preserved_yes_no_uncertain':'',
                    'useful_for_this_information_need_1_to_5':'','reviewer_code':'','review_date':'','notes':''})
                snippets=[]
                for rank,passage_id in enumerate(ids,1):
                    passage=corpus[passage_id]
                    snippets.append(f'<section><b>{rank}. {esc(passage_id)}</b><p>{esc(passage["raw_text"])}</p>'
                        f'<small>Supplied PDF page {passage["pdf_page"]}; <a href="{urls[source]}">Publisher source</a></small></section>')
                panels.append(f'<div class="panel"><h3>Panel {label}</h3>{"".join(snippets)}</div>')
            for added in dependency['dependency_additions']:
                if added not in seen_nodes:
                    seen_nodes.add(added);passage=corpus[added]
                    pilot_node_review.append({'chunk_id':added,'source':source,'text':passage['raw_text'],
                        'publisher_url':urls[source],'diagnostic_dependency_appropriate_yes_no_uncertain':'',
                        'complete_and_correct_scope_yes_no_uncertain':'','reviewer_code':'','notes':''})
            pilot_articles.append(f'<details><summary>{esc(cid)} · {esc(source)}</summary>'
                f'<h2>{esc(case["query"])}</h2><h3>Current findings</h3>'
                f'<pre>{esc(json.dumps(case["patient"],indent=2))}</pre><h3>Recorded history</h3>'
                f'<pre>{esc(json.dumps(case.get("history",[]),indent=2))}</pre>'
                f'<div class="panels">{"".join(panels)}</div></details>')
        write_csv(OUT/'pilot_panel_ratings.csv',pilot_ratings)
        write_csv(OUT/'dependency_candidate_review.csv',pilot_node_review)
        (OUT/'pilot_cases.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Balanced pilot review</title>'
            '<style>body{font:16px/1.6 system-ui;max-width:1400px;margin:auto;padding:24px;color:#17324d}'
            'details{padding:16px;border:1px solid #b9cbd5;margin:16px 0}summary{font-weight:bold;cursor:pointer}'
            '.panels{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}'
            'section{background:#f1f7f8;padding:12px;margin:12px 0;border-left:4px solid #087f8c}'
            'pre,p{white-space:pre-wrap}</style><h1>Balanced development pilot review</h1>'
            '<p>18 existing synthetic cases, six per source. Panel labels are shuffled per case. '
            'Review relevance and completeness independently before consulting engineering priorities. '
            'These are evidence sets, not care plans. No clinical review or superiority is asserted.</p>'
            +''.join(pilot_articles)+'</html>',encoding='utf8')
    (OUT/'synthetic_case_inputs.json').write_text(json.dumps([{k:c[k] for k in ['id','query','patient','history']}
        for c in cases],indent=2)+'\n',encoding='utf8')
    boundaries=DATA/'rag_development/recommendation_units/source_boundary_changes.json'
    if boundaries.exists():
        write_csv(OUT/'source_boundary_review.csv',[{
            'chunk_id':r['chunk_id'],'publisher_url':urls['NICE'],'supplied_pdf_pages':json.dumps(r['pdf_pages']),
            'old_text':r['old_text'],'corrected_text':r['new_text'],
            'corrected_text_sha256':r['new_text_sha256'],'extraction_span_json':json.dumps(r['source_span']),
            'boundary_correct_yes_no_uncertain':'','all_conditions_preserved_yes_no_uncertain':'',
            'scope_still_correct_yes_no_uncertain':'','reviewer_code':'','review_date':'','notes':''}
            for r in json.loads(boundaries.read_text())])
    topic_audit=DATA/'rag_development/recommendation_units/topic_scope/source_topic_review.csv'
    if topic_audit.exists():
        unique={}
        with topic_audit.open(encoding='utf8') as f:
            for row in csv.DictReader(f):unique[(row['id'],row['chunk_id'],row['reason'])]=row
        case_map={c['id']:c for c in cases}
        write_csv(OUT/'source_topic_exclusion_review.csv',[{
            'id':r['id'],'guideline':r['guideline'],'question':case_map[r['id']]['query'],
            'chunk_id':r['chunk_id'],'source_text':r['text'],'proposed_exclusion_reason':r['reason'],
            'exclusion_appropriate_yes_no_uncertain':'','still_relevant_conditionally_yes_no_uncertain':'',
            'reviewer_code':'','review_date':'','notes':''} for r in unique.values()])
    smoke=DATA/'rag_development/recommendation_units/scoped_primary_smoke'
    if (smoke/'summary.json').exists():
        corrected={c['chunk_id']:c for c in json.loads((smoke.parent/'corpus.json').read_text())['chunks']}
        case_map={c['id']:c for c in cases};smoke_panels=[];smoke_ratings=[]
        for case_id in json.loads((smoke/'development_protocol.json').read_text())['case_ids']:
            case=case_map[case_id];r=json.loads((smoke/'runs'/f'{case_id}.json').read_text())
            choices=[('candidate_order',r['candidate_ids'][:4]),('selected',r['selected_ids'][:4]),('consensus',r['consensus_ids'][:4])]
            rng.shuffle(choices);panels=[]
            for label,(method,passage_ids) in zip(['A','B','C'],choices):
                key.append({'study':'corrected_smoke','id':case_id,'panel':label,'method':method})
                smoke_ratings.append({'id':case_id,'guideline':r['guideline'],'panel':label,
                    'directly_relevant_passages_0_to_4':'','essential_evidence_omitted_yes_no_uncertain':'',
                    'wrong_population_or_timing_yes_no_uncertain':'','conditions_preserved_yes_no_uncertain':'',
                    'useful_for_this_question_1_to_5':'','reviewer_code':'','review_date':'','notes':''})
                snippets=[]
                for position,cid in enumerate(passage_ids,1):
                    c=corrected[cid]
                    snippets.append(f'<section><b>{position}. {esc(cid)}</b><p>{esc(c["raw_text"])}</p>'
                        f'<small>Supplied PDF page(s) {esc(str(c.get("pdf_pages",[c["pdf_page"]])))}; '
                        f'<a href="{urls[r["guideline"]]}">Publisher source</a></small></section>')
                panels.append(f'<div class="panel"><h3>Panel {label}</h3>{"".join(snippets) or "No passages selected."}</div>')
            smoke_panels.append(f'<details><summary>{esc(case_id)} · {esc(r["guideline"])}</summary>'
                f'<h2>{esc(case["query"])}</h2><h3>Current findings</h3><pre>{esc(json.dumps(case["patient"],indent=2))}</pre>'
                f'<h3>Recorded history</h3><pre>{esc(json.dumps(case["history"],indent=2))}</pre>'
                f'<div class="panels">{"".join(panels)}</div></details>')
        write_csv(OUT/'corrected_smoke_panel_ratings.csv',smoke_ratings)
        (OUT/'corrected_smoke_cases.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Corrected-source smoke review</title>'
            '<style>body{font:16px/1.6 system-ui;max-width:1400px;margin:auto;padding:24px;color:#17324d}'
            'details{padding:16px;border:1px solid #b9cbd5;margin:16px 0}summary{font-weight:bold;cursor:pointer}'
            '.panels{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}'
            'section{background:#f1f7f8;padding:12px;margin:12px 0;border-left:4px solid #087f8c}'
            'pre,p{white-space:pre-wrap}</style><h1>Corrected-source development smoke review</h1>'
            '<p>Three deliberately difficult existing synthetic cases. Shuffled evidence panels use the '
            'corrected corpus. Assess their relevance and missing conditions independently; no preferred '
            'answer or source approval is asserted. These are not care plans or a final study.</p>'
            +''.join(smoke_panels)+'</html>',encoding='utf8')
    # Keep the panel key separate from the clinician-facing ZIP.
    (DATA/'rag_development/clinician_panel_key.json').write_text(json.dumps(key,indent=2)+'\n',encoding='utf8')
    (OUT/'review_cases.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>NeoGuard development evidence review</title>'
        '<style>body{font:16px/1.6 system-ui;max-width:1200px;margin:auto;padding:24px;color:#17324d}'
        'details{border:1px solid #b9cbd5;padding:16px;margin:16px 0;border-radius:10px}summary{cursor:pointer;font-weight:700}'
        '.panels{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}'
        'section{background:#f1f7f8;padding:14px;margin:12px 0;border-left:4px solid #087f8c}pre{white-space:pre-wrap}'
        'p{white-space:pre-wrap}small{color:#405c70}</style><h1>NeoGuard development evidence review</h1>'
        '<p>100 synthetic cases. Panels A and B are randomly assigned per case. These are retrieved evidence sets, '
        'not treatment plans or clinically validated recommendations. Clinical ratings are uncompleted. '
        'Use the publisher source to check conditions, scope and source pagination.</p>'
        +''.join(articles)+'</html>',encoding='utf8')
    (OUT/'README.md').write_text('''# NeoGuard development review pack

This pack requests independent clinical adjudication; no clinical review has been performed or implied.
It contains 100 synthetic cases (NICE 40, AAP 30, WHO 30), no real patient records.
The same cases have informed engineering iterations. Repeated variants share question templates.

1. Open review_cases.html locally. Assess both evidence panels against the patient and question.
2. Complete panel_ratings.csv. Panel labels are shuffled per case; the method key is outside this bundle.
3. Use passage_relevance_review.csv to adjudicate the proposed candidate passages. Golds are not shown there.
4. Review source_scope_review.csv against original publisher documents. All approval fields start blank.
5. Only after independent relevance review, inspect engineering_priority_queue.csv. Its missed-gold counts
   are an engineering triage signal, not a clinical severity rating or evidence that existing labels are correct.
6. Use definition_context_review.csv to check exact publisher definitions and their section relations.
   Those supplemental definitions are not silently included as original top-four passages in the panels.
7. Open pilot_cases.html for 18 balanced development cases with three shuffled evidence panels.
   Complete pilot_panel_ratings.csv and dependency_candidate_review.csv. These pilots did not pass
   the engineering readiness gate. Assess future maternal counselling versus current infant actions,
   complete conditional frameworks and diagnostic limitations; do not force a preferred metric result.
   synthetic_case_inputs.json contains all 100 synthetic input cases and their recorded histories.
8. Review source_boundary_review.csv against the NICE publisher document. It proposes 14 structural
   corrections: separating risk-factor/indicator boxes from adjacent recommendations, restoring the
   cross-page Box 2 continuation and removing trailing numbered section headings. The existing
   evidence panels still describe their original development corpus; this separate amendment is not
   implicitly approved by those panels. Extraction offsets refer to a declared text stream, not PDF bytes.
9. Review source_topic_exclusion_review.csv: determine whether the proposed current-case topic routing
   removes useful conditional evidence. Its engineering exclusions have not received clinical approval.
10. Open corrected_smoke_cases.html and complete corrected_smoke_panel_ratings.csv. These three
    deliberately difficult cases use the corrected corpus and three shuffled evidence panels.
    Adjudicate useful alternative passages and omissions before comparing against engineering golds.

Priority clinical issues include CRP-alone reasoning, persistent symptoms with a negative culture,
separate culture-incubation and antibiotic-exposure clocks, critical illness versus isolated fast breathing,
missing observations, AAP gestational eligibility, WHO hospital/referral conditions and complete qualifiers.
Check whether unlabelled retrieved passages are also relevant; do not accept or reject a gold solely to raise a metric.

These panels evaluate retrieval only. Do not use their ratings as care-plan usability or treatment-safety results.
The separate earlier 100-case care-plan bundle concerns the frozen baseline, not this new candidate.
No patient-specific treatment decision or clinical approval should be inferred from an exact quotation.
The clinical source registry remains pending review. Do not enter names, identifiers or real cases into this pack.

Source links: NICE NG195 https://www.nice.org.uk/guidance/ng195 ; AAP https://doi.org/10.1542/peds.2018-2894 ;
WHO https://www.who.int/publications/i/item/9789240102903 . PDF-page numbers refer to the supplied extracts,
and their mapping to complete publisher documents also requires checking.
''',encoding='utf8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'}
    (OUT/'manifest.json').write_text(json.dumps({'stage':'development_only','cases':100,'seed':31,
        'balanced_pilot_cases':18 if pilot_ratings else 0,'balanced_pilot_panel_rows':len(pilot_ratings),
        'corrected_smoke_panel_rows':len(smoke_ratings) if (smoke/'summary.json').exists() else 0,
        'source_boundary_proposals':len(json.loads(boundaries.read_text())) if boundaries.exists() else 0,
        'source_topic_exclusion_reviews':len(unique) if topic_audit.exists() else 0,
        'clinical_review_status':'not performed','ratings_blank':True,'files_sha256':hashes},indent=2)+'\n',encoding='utf8')
    archive=OUT.parent/'neoguard-development-clinician-review.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()):
            if p.is_file():z.write(p,p.name)
    print(json.dumps({'bundle':str(archive),'cases':100,'panels':len(ratings),'passages':len(relevance),
                     'scope_rows':len(scope),'review_status':'uncompleted'}))


if __name__=='__main__':main()
