"""Local, self-contained clinician adjudication bundle; no external sending."""
from __future__ import annotations
import csv
import hashlib
import html
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
DATA=ROOT/'output/research/expanded100'
OUT=ROOT/'output/clinician-review/neoguard-100-case-review'

def read(path):
    return json.loads(path.read_text(encoding='utf8'))

def build():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from xml.sax.saxutils import escape
    OUT.mkdir(parents=True,exist_ok=True)
    cases=read(DATA/'cases.json')
    corpus=read(DATA/'corpus.json')
    manifest=read(DATA/'manifest.json')
    index={c['chunk_id']:c for c in corpus['chunks']}
    case_meta={c['id']:c for c in manifest['cases']}
    queue=read(DATA/'clinician_review_queue.json')
    priority={r['case_id']:r['priority'] for r in queue}
    for name in ['cases.json','corpus.json','manifest.json','protocol.json','benchmark_report.md','clinician_review_queue.json']:
        shutil.copy2(DATA/name,OUT/name)
    # A reviewer may already have completed the CSV. Preserve their entries by
    # case ID on rebuild; never replace clinical annotations with blank cells.
    rating_path=OUT/'clinician_ratings.csv'
    existing={}
    if rating_path.exists():
        with rating_path.open(encoding='utf8',newline='') as f:
            existing={r['case_id']:r for r in csv.DictReader(f)}
    fields=['case_id','guideline','family','priority','reviewer_name','review_date','scope_applicable_yes_no_uncertain',
            'case_plausibility_1_to_5','critical_missing_input','proposed_gold_correct_yes_no_partial',
            'missing_or_irrelevant_gold_ids','reference_clinically_acceptable_yes_no_partial',
            'reference_correction','candidate_grounding_1_to_5','candidate_patient_fidelity_1_to_5',
            'candidate_completeness_1_to_5','candidate_actionability_1_to_5','candidate_uncertainty_1_to_5',
            'potential_harm_none_minor_major_critical','harm_or_missing_condition','would_use_after_clinician_review_yes_no_uncertain',
            'adjudication_status_not_reviewed_accepted_revise_exclude','comments']
    with rating_path.open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        for c in cases:
            row={k:'' for k in fields}
            row.update({'case_id':c['id'],'guideline':case_meta[c['id']]['guideline'],'family':c['family'],'priority':priority[c['id']],
                        'adjudication_status_not_reviewed_accepted_revise_exclude':'not_reviewed'})
            row.update({k:v for k,v in existing.get(c['id'],{}).items() if k in fields and k not in ['case_id','guideline','family','priority']})
            writer.writerow(row)
    results={}
    html_cases=[]
    for c in cases:
        run_path=DATA/'runs'/f'{c["id"]}.json'
        candidate=None
        if run_path.exists():
            record=read(run_path)
            # Do not expose an incomplete provider execution as a clinical answer.
            from scripts.evaluation_transport import quality_eligible
            if quality_eligible(record):
                claims=record['result'].get('draft',{}).get('claims',[])
                candidate=[claim['text'] for claim in claims]
        results[c['id']]={'case_id':c['id'],'candidate':candidate,'status':'pending' if candidate is None else 'completed'}
        g=case_meta[c['id']]['guideline']
        esc=html.escape
        sources=''.join(f'<section class="source"><h4>{esc(key)} | PDF page {index[key]["pdf_page"]}</h4><p>{esc(index[key]["text"])}</p><small>Text SHA-256: {index[key]["text_sha256"]}</small></section>' for key in c['gold_chunk_ids'])
        answer='<p class="pending">Generation/evaluation pending; no completed clinical candidate is represented.</p>' if candidate is None else '<ol>'+''.join('<li>'+esc(x)+'</li>' for x in candidate)+'</ol>' if candidate else '<p>No structurally valid discussion draft was produced.</p>'
        html_cases.append(f'''<article data-guideline="{g}" data-family="{c['family']}" data-priority="{priority[c['id']]}">
<h2>{esc(c['id'])}</h2><p class="tag">{g} | {esc(c['family'])} | priority: {priority[c['id']]}</p>
<h3>Clinical question</h3><p>{esc(c['query'])}</p><h3>Recorded observations</h3><pre>{esc(json.dumps(c['patient'],indent=2))}</pre>
<h3>Earlier observations</h3><pre>{esc(json.dumps(c['history'],indent=2))}</pre>
<details><summary>Candidate discussion points (assess before viewing proposed reference)</summary>{answer}</details>
<details><summary>Proposed reference and gold passages - engineering authored, not clinician approved</summary><p>{esc(c['reference'])}</p>{sources}</details>
<p class="small">Record adjudication in clinician_ratings.csv using this case ID. Case SHA-256: {case_meta[c['id']]['sha256']}</p></article>''')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>NeoGuard: 100-case clinician review</title><style>
body{font:16px/1.6 system-ui,sans-serif;background:#f3f6f9;color:#19314a;margin:0}main,header{max-width:1000px;margin:auto;padding:24px}header{background:#fff}h1{font-size:28px}h2{font-size:23px}h3{margin-top:24px}article{background:white;border:1px solid #cbd5e1;border-left:5px solid #087f8c;border-radius:8px;padding:26px;margin:24px 0}pre{white-space:pre-wrap;background:#f2f6fa;padding:16px;font-size:14px}summary{cursor:pointer;font-weight:700;padding:12px;background:#e7f2f4}details{margin:14px 0}details>p,details>ol{padding:12px 24px}.source{border-top:1px solid #ccd8e3;padding:12px 0}.source small,.small{font-size:12px;overflow-wrap:anywhere}.tag{color:#08616b;font-weight:600}.pending{color:#7b4300}select,input{padding:10px;margin:6px;border:1px solid #a9bbc8;font:inherit}nav{position:sticky;top:0;background:#fff;border-bottom:1px solid #ccc;padding:10px;z-index:3}@media print{nav{display:none}article{break-before:page}details>*{display:block}summary{display:block}}
</style><header><h1>NeoGuard: clinician adjudication</h1><p>Exactly 100 synthetic cases: NICE 40, AAP 30, WHO 30. No real patient data. All ratings are blank until a clinician supplies them. This is a research review packet.</p><p>Assess observations and candidate first; then open the proposed reference. Record scope errors, missing conditions and potential harm explicitly. Do not interpret source hashes as proof of clinical correctness.</p><p><a href="clinician_ratings.csv">Ratings CSV</a> | <a href="review_handbook.pdf">Review handbook</a> | <a href="benchmark_report.md">Benchmark description</a></p></header><nav><label>Guideline <select id="guideline"><option>All</option><option>NICE</option><option>AAP</option><option>WHO</option></select></label><label>Family <select id="family"><option>All</option>'''+''.join(f'<option>{f}</option>' for f in sorted({c['family'] for c in cases}))+'''</select></label><label>Priority <select id="priority"><option>All</option><option>high</option><option>standard</option></select></label><label>Find <input id="search" placeholder="Case ID or term"></label><strong id="count"></strong></nav><main>'''+''.join(html_cases)+'''</main><script>
function filter(){let n=0;document.querySelectorAll('article').forEach(a=>{let ok=['guideline','family','priority'].every(k=>document.getElementById(k).value==='All'||a.dataset[k]===document.getElementById(k).value);ok=ok&&a.textContent.toLowerCase().includes(document.getElementById('search').value.toLowerCase());a.hidden=!ok;if(ok)n++});document.getElementById('count').textContent=n+' cases'}document.querySelectorAll('select,input').forEach(e=>e.addEventListener('input',filter));filter();</script></html>'''
    (OUT/'review.html').write_text(page,encoding='utf8')
    (OUT/'candidate_snapshot.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
    guide=ROOT/'output/pdf/neoguard-100-case-review-handbook.pdf'
    guide.parent.mkdir(exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyClinical',fontName='Helvetica',fontSize=10.5,leading=16,spaceAfter=10,textColor=colors.HexColor('#19314a')))
    styles['Heading1'].textColor=colors.HexColor('#16324f')
    styles['Heading2'].textColor=colors.HexColor('#087f8c')
    story=[]
    def p(text,style='BodyClinical'):
        story.append(Paragraph(text,styles[style]))
    p('NeoGuard EOS<br/>Clinician Review Handbook','Title')
    p('100 synthetic cases | NICE 40 | AAP 30 | WHO 30','Heading2')
    p('Purpose: adjudicate case plausibility, guideline applicability, proposed gold passages, reference answers and available generated discussion points. This packet does not constitute clinical validation, source approval or authorization for patient care.')
    p('What is included','Heading2')
    for text in ['review.html: offline, searchable case viewer. Open locally in a browser; it requires no server or sign-in.',
                 'clinician_ratings.csv: one row per case with blank rating and correction fields. Preserve case IDs when returning the completed file.',
                 'cases.json and corpus.json: synthetic inputs, proposed references and exact indexed passages. manifest.json records case and passage hashes.',
                 'candidate_snapshot.json: completed candidates where available. Pending runs are explicitly labelled and are not fabricated.']:
        p('- '+text)
    p('Review order','Heading2')
    p('Candidates are question-specific discussion points under the frozen research protocol. They are not complete thirteen-section application care plans. Rate completeness against the stated clinical question.')
    p('If no structured candidate is available, leave its candidate-rating fields blank and note the missing output. The case, proposed reference and gold passages can still be adjudicated.')
    p('First examine the question and observations. Assess whether the setting, gestation, age, illness signs and timeline are internally coherent. Review the candidate before opening the proposed reference to reduce reference anchoring. Then inspect the source passages and correct the proposed gold set. Finally record potential harm, required changes and an accept/revise/exclude decision.')
    p('No ratings have been supplied by a clinician. Technical source checks and automated judges are engineering checks only. A reviewer may decline or exclude a case; exclusions should retain their reason and original case ID.')
    story.append(PageBreak())
    p('Guideline scope and priority checks','Heading1')
    for title,text,url in [
        ('NICE NG195 - 40 cases','The original 18 vignettes remain unchanged. The corpus is the frozen original 132-passage extraction, including known recommendation-boundary and box-extraction concerns. Prioritize negative-culture stopping eligibility, CRP-only reasoning and preterm applicability. Check whether every clinically relevant qualifier is present in each proposed gold passage.','https://www.nice.org.uk/guidance/ng195'),
        ('AAP 2018, infants at least 35 weeks - 30 cases','The report is Pediatrics e20182894, DOI 10.1542/peds.2018-2894. All AAP cases are at least 35 weeks. Review the 36-48-hour sterile-culture guidance together with its term critical-illness exception. NICE monitoring intervals and its four-condition stopping rule must not be silently attributed to AAP.','https://doi.org/10.1542/peds.2018-2894'),
        ('WHO 2024, birth-to-72-hour subset - 30 cases','The source covers serious bacterial infections at 0-59 days. Only newborn cases below 72 hours are evaluated here. Check community versus hospital scope, referral feasibility and isolated fast-breathing eligibility. WHO does not supply a validated maternal-risk or gestation-specific subgroup score in these passages. Hospital diagnostic evidence gaps and antibiotic-duration differences require particular review.','https://www.who.int/publications/i/item/9789240102903')]:
        p(title,'Heading2');p(text);p(f'<link href="{url}" color="#087f8c">Primary source</link>')
    p('Source provenance','Heading2')
    p('The WHO supplied PDF is an excerpt with local PDF page 1 corresponding to printed page 17. Gold passage metadata includes both page systems. Hashes identify the supplied bytes; they do not establish that an extract retains every clinical condition. Production source approval remains pending and unchanged.')
    story.append(PageBreak())
    p('Rating rubric and return instructions','Heading1')
    p('Use 1 = major deficiency, 2 = substantial deficiency, 3 = mixed/needs revision, 4 = mostly adequate, 5 = fully adequate for the stated synthetic task. Use text fields to describe the deficiency rather than relying on a score alone.')
    rubric=[('Grounding','Every substantive recommendation follows from its cited passage, including population, negation and conditions.'),
            ('Patient fidelity','Patient facts, missingness and temporal direction are represented accurately; unknowns are not normal.'),
            ('Completeness','Required assessment, uncertainty and source-supported actions are covered without filling gaps with invented guidance.'),
            ('Actionability','The discussion is legible and useful to a clinician while preserving local decision making and conditional guidance.'),
            ('Uncertainty','Diagnostic and source limitations are stated accurately; no unsupported reassurance or individual probability is inferred.'),
            ('Potential harm','None, minor, major or critical. State the specific unsupported treatment, omitted condition, delayed assessment or other mechanism.')]
    for title,text in rubric:
        p(title,'Heading2');p(text)
    p('Units and missingness','Heading2')
    p('age_hours and observation ages are hours since birth; gestational_age_weeks is weeks; respiratory_rate is breaths/min; spo2 is percent; temperature_c is Celsius. CRP values in the added engineering cases are intended as mg/L; legacy cases do not carry explicit assay metadata, which should be flagged if material. Null, unknown and unavailable are missing information. No normal range or diagnostic threshold should be inferred from the synthetic numbers alone.')
    p('Return the completed CSV and any annotated sources to the study owner. Do not add real patient information to this synthetic packet. Rebuilding the bundle preserves existing reviewer entries by case ID. The study owner should version adjudicated revisions separately; the frozen benchmark must not be silently overwritten.')
    def footer(canvas,document):
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(colors.HexColor('#496078'))
        canvas.drawString(44,25,'NEOGUARD | SYNTHETIC RESEARCH ADJUDICATION | CLINICAL REVIEW PENDING')
        canvas.drawRightString(A4[0]-44,25,str(document.page))
    SimpleDocTemplate(str(guide),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=45,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
    shutil.copy2(guide,OUT/'review_handbook.pdf')
    (OUT/'README.md').write_text('# NeoGuard 100-case clinician review\n\nOpen review.html, read review_handbook.pdf and complete clinician_ratings.csv. All cases are synthetic. NICE 40; AAP 30; WHO 30. No clinician sign-off is implied. Candidate entries marked pending require a later refreshed bundle before output adjudication. Existing reviewer CSV entries are preserved on rebuild.\n',encoding='utf8')
    file_hashes={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='bundle_hashes.json'}
    (OUT/'bundle_hashes.json').write_text(json.dumps(file_hashes,indent=2)+'\n')
    target=OUT.parent/'neoguard-100-case-clinician-review.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.iterdir()):
            if path.is_file():
                archive.write(path,OUT.name+'/'+path.name)
    print({'cases':len(cases),'completed_candidate_snapshots':sum(v['status']=='completed' for v in results.values()),'bundle':str(target),'pdf':str(guide)})

if __name__=='__main__':
    build()
