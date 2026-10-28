"""Summarise measured failures and preserve research boundary/provenance."""
import csv,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'output/research/rag_development'


def main():
    fresh=json.loads((BASE/'wording_audit/summary.json').read_text())
    repair=json.loads((BASE/'canonical_router_repair/fresh/summary.json').read_text())
    pilot=json.loads((BASE/'patient_explanation_v5/summary.json').read_text())
    audit=json.loads((BASE/'generalization_audit/summary.json').read_text())
    wording=list(csv.DictReader((BASE/'generalization_audit/paraphrase_clinician_review.csv').open()))
    report={'stage':'development_only','final_evaluation_allowed':False,'clinical_ready':False,
        'base_synthetic_cases':100,'distinct_focused_templates':sum(audit['unique_focused_queries'].values()),
        'wording_transform_slots':len(wording),'changed_wording_slots':sum(r['original_query']!=r['perturbed_query'] for r in wording),
        'fresh_original_replay_matches':fresh['original_replay_matches'],
        'independent_holdout':False,'clinical_review_completed':False,'new_retrieval_groq_calls':0,
        'attempted_explanation_cases':pilot['quality_completed'],'planned_explanation_cases':pilot['planned'],
        'model_released_explanations':pilot['whole_draft_released'],
        'attempted_release_coverage':pilot['whole_draft_released']/pilot['quality_completed'],
        'planned_release_coverage':pilot['release_coverage_over_planned'],
        'blockers':[
            'NICE plain-wording fixed-plan Recall@4 remains 0.7667 after intent normalization (below 0.8 development target).',
            'AAP model-approved action prose omits a site-specific-infection exception; agreement does not establish semantic completeness.',
            'NICE draft mistakes unclear suspicion for reassuring eligibility and adds unsupported escalation; only a different structural issue blocks release.',
            'WHO model auditors disagree on illness-category conflation.',
            'Balanced usable-answer coverage and fresh semantic fault suite remain incomplete.',
            'Clinical source approval, gold adjudication, paraphrase equivalence and independent challenge cases remain unavailable.'
        ],'nonclinical_fallback':'100 lossless evidence views preserve full passages and separate observed facts/unknowns; not a care-plan usability result.',
        'app_integration':'new research candidates not promoted','github_push':'not performed'}
    out=BASE/'robustness_audit';out.mkdir(exist_ok=True)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    rows=[]
    for data,phase in [(fresh,'fresh_wording_legacy'),(repair,'fresh_wording_posthoc_canonical')]:
        for r in data['statistics']:
            rows.append({'phase':phase,**r})
    with (out/'all_retrieval_metrics.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    paper=(ROOT/'docs/research/manuscript.md').read_text(encoding='utf8')
    old=(BASE/'manuscript_before_publication.md').read_text(encoding='utf8')
    def tables(text):
        s=text.split('## 6. Synthetic RAG experimental protocol')[1].split('## 8. Discussion and limitations')[0]
        return re.findall(r'(?:^\|.*(?:\n|$))+',s,re.M)
    historical=tables(old);current=tables(paper)
    if len(historical)!=7 or not all(t in current for t in historical):raise ValueError('Historical table changed')
    digest=hashlib.sha256((ROOT/'backend/rag/verification_graph.py').read_bytes()).hexdigest()
    if digest!='07b51352374f1dac88b236b9b5cf6199396b20218cb6131a7b4e3783dd17b07c':raise ValueError('Frozen graph changed')
    integrity={'historical_tables_checked':7,'all_historical_table_values_preserved':True,
        'full_historical_prose_identical':False,'additional_annotation_ceiling_table':True,
        'prose_amendments':'Post-hoc scope, annotation ceilings and measured robustness/safety limitations; historical numerical tables retained.',
        'paper_sha256':hashlib.sha256((ROOT/'docs/research/manuscript.md').read_bytes()).hexdigest(),
        'frozen_verification_core_sha256':digest}
    (BASE/'paper_integrity.json').write_text(json.dumps(integrity,indent=2)+'\n')
    from robustness_paper_sections import sections
    summary='# RAG robustness audit and paper-inspired ML comparison\n\nFinal evaluation, candidate app integration and GitHub push remain on hold.\n\n'+sections()
    (ROOT/'docs/research/rag_robustness_audit.md').write_text(summary,encoding='utf8')
    note='\n\n## 28 October robustness audit\n\n'+ '\n'.join('- '+b for b in report['blockers'])+'\n\nFull numerical results and confidence intervals: output/research/rag_development/robustness_audit/all_retrieval_metrics.csv. No unchanged original-query score is evidence of independent generalisation.\n'
    for filename in ['docs/research/final_evaluation_gate.md','docs/research/rag_remaining_gaps.md','docs/research/evaluated_pipeline_app_handoff.md']:
        p=ROOT/filename;text=p.read_text().split('\n\n## 28 October robustness audit')[0];p.write_text(text+note,encoding='utf8')
    card=ROOT/'docs/research/pic_longitudinal_model_card.md';marker='\n\n## Paper-inspired Bayesian comparison'
    text=card.read_text().split(marker)[0]
    text+=marker+'''

The attached Nguyen et al. paper (https://doi.org/10.21037/tp-22-510) studies broad paediatric diagnosis, not the same pre-culture neonatal endpoint. Its AUROC 0.866 and sensitivity 0.463 do not validate this model. A local naive-Bayes/TAN comparison retains the strict cohort, training-only discretization and structure learning, patient-disjoint folds, equal infant weights, and all seeds 31/47/83. Missingness has an explicit state, not an assumed normal value.

At seed 31 snapshot TAN AUROC is 0.575012 (patient-bootstrap 95% CI 0.389438–0.750369). Longitudinal TAN AUROC is 0.403278, 0.430975 and 0.453482 for the three declared seeds. All 12 arms/seeds are retained in output/research/pic_longitudinal/paper_inspired_bayes/metrics.csv, with 2,000-resample infant-level and paired intervals. No favourable seed, posterior extreme or architecture is promoted as a clinical EOS risk. Calibration is unestablished; all new models remain withheld. Seven independent positive infants are insufficient to establish a robust clinical model through further architecture search.
'''
    card.write_text(text,encoding='utf8')
    print(json.dumps({'report':str(out/'summary.json'),'historical_tables_preserved':True,'final_evaluation_allowed':False}))


if __name__=='__main__':main()
