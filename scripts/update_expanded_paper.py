"""Replace only affected RAG passages after the entire declared study completes."""
from __future__ import annotations
import csv
import argparse
import difflib
import itertools
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'output/research/expanded100'
SOURCE=ROOT/'docs/research/manuscript.md'

def read(path):
    return json.loads(path.read_text(encoding='utf8'))

def plot_results(summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    groups=['NICE','AAP','WHO']
    methods=['lexical','dense','hybrid','hybrid_concepts']
    fig,axes=plt.subplots(3,1,figsize=(8.5,9),layout='constrained')
    palette=['#8093a6','#4389b5','#087f8c','#b47739']
    x=np.arange(3)
    for i,method in enumerate(methods):
        values=[next(r['mean'] for r in summary['retrieval'] if r['guideline']==g and r['method']==method and r['metric']=='recall_at_4') for g in groups]
        axes[0].bar(x+(i-1.5)*.19,values,width=.18,color=palette[i],label=method.replace('_',' '))
    axes[0].set(xticks=x,xticklabels=groups,ylabel='Recall@4',ylim=(0,1),title='A. Fixed retrieval methods, separate guideline indexes')
    axes[0].legend(ncol=2,fontsize=8,frameon=False)
    for i,arm in enumerate(['without_verification','verified_all_cases']):
        rows=[next(r for r in summary['alignment'] if r['guideline']==g and r['arm']==arm and r['metric']=='bert_f1') for g in groups]
        bars=axes[1].bar(x+(i-.5)*.32,[r['coverage'] for r in rows],width=.30,color=['#4389b5','#087f8c'][i],label=['Unverified','Verified'][i])
        for bar,r in zip(bars,rows):
            axes[1].text(bar.get_x()+bar.get_width()/2,bar.get_height()+.02,f'{r["emitted"]}/{r["quality_n"]}',ha='center',fontsize=9)
    axes[1].set(xticks=x,xticklabels=groups,ylabel='Emission coverage',ylim=(0,1.16),title='B. Available discussion points after release filtering')
    axes[1].legend(frameon=False,fontsize=9)
    rows=[next(r for r in summary['alignment_paired'] if r['guideline']==g and r['metric']=='bert_f1') for g in groups]
    for i,kind in enumerate(['case','family']):
        means=np.array([r['mean'] for r in rows]); low=np.array([r[kind+'_low'] for r in rows]); high=np.array([r[kind+'_high'] for r in rows])
        axes[2].errorbar(means,x+(i-.5)*.12,xerr=[means-low,high-means],fmt='o',capsize=4,color=['#16324f','#b47739'][i],label=kind+' bootstrap 95% CI')
    axes[2].axvline(0,color='#7a8793',linewidth=1,linestyle='--')
    axes[2].set(yticks=x,yticklabels=groups,xlabel='Verified minus unverified DistilBERT F1',title='C. Alignment cost of withholding the same initial draft')
    axes[2].legend(frameon=False,fontsize=8)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
        ax.grid(axis='y',alpha=.15)
    dest=ROOT/'output/research/figures/rag_expanded_results.png'
    dest.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(dest,dpi=220)
    plt.close(fig)

def main(preview=False):
    summary=read(DATA/'tables_summary.json')
    if not summary['complete_primary_metrics'] or len(summary['faults'])!=3 or (not preview and len(summary['resolution'])!=6):
        raise SystemExit('Study incomplete: refusing to insert provisional results into the manuscript.')
    if any(r['quality_n']!=12 for r in summary['faults']):
        raise SystemExit('Fault execution incomplete')
    counts={'NICE':40,'AAP':30,'WHO':30}
    if not preview and any(r['paired_n']!=counts[r['guideline']] for r in summary['resolution']):
        raise SystemExit('Bounded-resolution paired execution incomplete')
    if any(r['quality_n']!=counts[r['guideline']] for r in summary['alignment']):
        raise SystemExit('Primary population incomplete')
    if any(not (DATA/'judges'/f'{c["id"]}.json').exists() for c in read(DATA/'cases.json')):
        raise SystemExit('Blinded-judge execution incomplete')
    old=(ROOT/'output/research/expanded/historical/manuscript.md').read_text(encoding='utf8')
    current=SOURCE.read_text(encoding='utf8')
    saved_after=DATA/'paper_revision/manuscript_after.md'
    if current!=old and (not saved_after.exists() or current!=saved_after.read_text(encoding='utf8')):
        raise SystemExit('Manuscript has intervening edits outside the generated revision; preserve and reconcile them manually.')
    text=old.replace('Updated 26 October 2026','Updated 27 October 2026')
    if preview:
        text=text.replace('## Abstract','**INTERNAL LAYOUT PREVIEW - bounded-resolution study remains incomplete.**\n\n## Abstract',1)
    cases=read(DATA/'cases.json')
    metrics=read(DATA/'per_case_metrics.json')
    released=sum(r['released'] for r in metrics)
    generated=sum(bool(r['candidate']) for r in metrics)
    def f(x):
        return 'NA' if x is None else f'{x:.2e}' if 0<abs(x)<.0001 else f'{x:.4f}'
    def interval(row,prefix='case'):
        return f'[{f(row[prefix+"_low"])}, {f(row[prefix+"_high"])}]'
    def estimate(g,arm,metric):
        return next(r for r in summary['alignment'] if r['guideline']==g and r['arm']==arm and r['metric']==metric)
    def section(start,end,body):
        nonlocal text
        a,b=text.index(start),text.index(end)
        text=text[:a]+start+'\n\n'+body.strip()+'\n\n'+text[b:]
    abstract_old='Separately, 18 synthetic vignettes and 12 injected faults examine retrieval, text alignment, model-based judging and release behavior. Hybrid retrieval obtains Recall@4 0.6667; concept expansion obtains 0.5833. The revised generator produces 15/18 structured drafts, of which 4/18 are released after verification.'
    abstract_new=(f'Separately, 100 synthetic vignettes (40 NICE, 30 AAP 2018 and 30 WHO 2024) and 36 injected faults examine retrieval, text alignment, model-based judging and release behavior. '
        f'The generator produces {generated}/100 structured drafts and verification releases {released}/100. '
        'Retrieval results are stratified by guideline; concept expansion has lower measured Recall@4 than hybrid retrieval for all three sources in this benchmark, with paired case and scenario-family intervals reported.')
    assert abstract_old in text
    text=text.replace(abstract_old,abstract_new)
    text=text.replace('A subsequent ten-case historical pilot','A separate ten-case historical pilot')
    old_corpus='The synthetic experiment uses a distinct evaluation-only extraction from the user-supplied May 2026 NICE PDF. Recommendation-level passages retain conditional lists across page breaks, including all conditions of the 36-hour stopping recommendation. Two risk/indicator boxes supplement these passages, producing 132 chunks. The local cropped PDF page number is retained separately from guideline section identifiers. The experimental extraction does not mark the production registry as clinically approved, and other available PDFs are not silently mixed into this benchmark.'
    new_corpus=('The synthetic experiment uses separate evaluation-only indexes for NICE NG195 (132 frozen passages), the AAP 2018 report for infants born at least 35 weeks (43 passages), and WHO 2024 serious bacterial infection guidance (141 passages). '
        'AAP summary recommendations and complete article paragraphs and WHO recommendations, qualifiers and scope paragraphs retain source-page metadata and SHA-256 identities. WHO cases are restricted to the first 72 hours and preserve hospital, non-hospital and referral-feasibility conditions. '
        'The source-gated benchmark contains 100 cases; it does not mark any production source as clinically approved. Paragraph granularity and candidate-pool sizes differ across guidelines; original NICE extraction-boundary concerns remain for clinician adjudication.')
    assert old_corpus in text
    text=text.replace(old_corpus,new_corpus)
    section('### 6.1 Cases, references and retrieval ablations','### 6.2 Paired verification ablation and provider failures',
        'One hundred synthetic vignettes include the original 18 unchanged cases and 82 additions: 40 NICE, 30 AAP and 30 WHO cases. The six families remain respiratory deterioration, CRP-only reasoning, incomplete stopping criteria, initial investigations, an isolated known risk factor and missing results. Added cases vary gestation, age, care setting and observation availability. Every gold ID resolves to an indexed passage, and case, source and passage hashes are recorded with seed 31. References are engineering-authored rather than clinician-adjudicated. Related variants share templates; 100 cases do not represent 100 independent clinical scenarios.\n\n'
        'Each guideline is searched against its source-only candidate pool. The original BM25, MiniLM-L6-v2 normalized exact-cosine, reciprocal-rank hybrid and hybrid-plus-concepts implementations remain unchanged, with RRF offset 60 and four returned passages. The original 18 retrieval rankings replay exactly. Recall@4 is the fraction of proposed relevant IDs retrieved; MRR@4 is the reciprocal rank of the first relevant ID. WHO exact-text PDF duplicates were removed in a logged structural index amendment. A superseded 114-case retrieval-only prototype remains archived; the user-requested 100-case allocation used predetermined family quotas and case order rather than score-based selection. No retrieval hyperparameter was tuned after results were observed.\n\n'
        'AAP and WHO source identity and recommendation spans were technically checked, but clinical source approval and gold adjudication remain pending. Passage-level age, gestation and setting annotations are stored for review; the frozen source-gated retriever does not apply those passage-level filters. WHO evidence gaps, referral conditions and treatment-duration statements are not replaced with NICE or AAP rules. Overlapping narrative spans can be relevant even when absent from the proposed gold-ID set, limiting strict ID-based recall interpretation. The experiment measures offline concept expansion rather than live Neo4j or pgvector performance.')
    # Retain the original paired protocol while disclosing the runtime limitation.
    marker='This eligibility rule separates model performance from service availability.'
    text=text.replace(marker,marker+' The historical and current verifier source hashes differ; the expanded study reruns the original cases with the current frozen verifier and logs this runtime drift. Current auditor completions are limited to 1,000 tokens and resolution completions to 2,200 tokens. The retained historical runner used transport defaults rather than forwarding completion options, so exact historical verifier/transport equivalence is not asserted. Model temperature remains zero; no provider sampling seed or immutable model snapshot is available. Completed role responses are checkpointed by prompt hash and audit-round occurrence.')
    text=text.replace('Twelve injected drafts, four fault types with three variants each,','Thirty-six injected drafts, twelve per guideline with four fault types and three variants each,')
    text=text.replace('Versions and BERTScore configuration hashes are saved.','Versions and BERTScore configuration hashes are saved. Descriptive 95% intervals use 2,000 resamples with seed 31: paired case resampling and whole-scenario-family resampling. Unequal family sizes retain their case weights; six families provide limited cluster-level inference.')
    retrieval=['Table 5. Source-stratified retrieval; brackets show paired-case bootstrap 95% intervals for each estimate. Full scenario-family intervals and paired method contrasts are provided in the CSV tables.','',
        '| Guideline (N) | Retriever | Recall@4 [95% CI] | MRR@4 [95% CI] |','| --- | --- | --- | --- |']
    for g in counts:
        for method in ['lexical','dense','hybrid','hybrid_concepts']:
            rows=[r for r in summary['retrieval'] if r['guideline']==g and r['method']==method]
            a=next(r for r in rows if r['metric']=='recall_at_4');b=next(r for r in rows if r['metric']=='mrr_at_4')
            retrieval.append(f'| {g} ({counts[g]}) | {method.replace("_"," ")} | {f(a["mean"])} {interval(a)} | {f(b["mean"])} {interval(b)} |')
    retrieval+=['','For hybrid-plus-concepts minus hybrid, Recall@4 differences are: '+ '; '.join(
        f'{r["guideline"]} {f(r["mean"])} (case {interval(r)}, family {interval(r,"family")})' for r in summary['retrieval_paired'] if r['metric']=='recall_at_4')+'.', '',
        'The measured concept-expansion scores do not support a blanket graph benefit. The original 18 rankings are unchanged; differences between the old NICE average and the expanded NICE average reflect the additional queries rather than a changed retrieval algorithm. Source-stratified counts, candidate-pool asymmetry and engineering-authored relevance judgments limit generalization; no source-pooled headline retrieval score is used.']
    section('### 7.2 Retrieval and concept expansion','### 7.3 Generation, verification and coverage','\n'.join(retrieval))
    alignment=[f'All 100 declared cases completed provider execution. Parsed discussion drafts were produced for {generated}/100 cases and {released}/100 were released. Structural failures and completed auditor dissent remain quality outcomes. The paired arms share the same initial draft; verification changes release rather than wording.', '',
        'Table 6. Source-stratified alignment and emission coverage. Conditional scores retain source-population coverage rather than displaying conditional coverage as 100%. All-case withheld responses have zero alignment. Full lexical/semantic estimates and both bootstrap interval types appear in CSV tables.', '',
        '| Guideline | Arm | Scored N | Emitted / quality N | BLEU-4 | METEOR | ROUGE-L | DistilBERT F1 | RoBERTa F1 |','| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for g in counts:
        for arm in ['without_verification','verified_all_cases','released_only','generated_only']:
            a=estimate(g,arm,'bert_f1')
            # Corpus BLEU is reported for all-case arms only, avoiding any
            # substitution of sentence-average BLEU for corpus aggregation.
            bleu=next((r['mean'] for r in summary['alignment'] if r['guideline']==g and r['arm']==arm and r['metric']=='corpus_bleu4'),None)
            values=[bleu]+[estimate(g,arm,m)['mean'] for m in ['meteor','rougeL','bert_f1','roberta_f1']]
            alignment.append(f'| {g} | {arm.replace("_"," ")} | {a["scored_n"]} | {a["emitted"]}/{a["quality_n"]} | '+' | '.join(f(v) for v in values)+' |')
    alignment+=['','Corpus BLEU brevity penalties strongly reflect withheld output length; very small all-case values do not measure a rewriting effect.', '',
        'Table 7. Paired all-case verified-minus-unverified DistilBERT F1; negative values reflect the coverage cost of withholding the same draft.', '',
        '| Guideline | Paired N | Released / N | Difference | Case 95% CI | Family 95% CI |','| --- | --- | --- | --- | --- | --- |']
    for r in summary['alignment_paired']:
        if r['metric']=='bert_f1':
            alignment.append(f'| {r["guideline"]} | {r["n"]} | {r["released"]}/{r["n"]} | {f(r["mean"])} | {interval(r)} | {interval(r,"family")} |')
    alignment+=['','Released-only comparisons are selected-population comparisons. A released draft has identical wording in both arms, so verification cannot improve that draft through rewriting in this experiment. Alignment and release counts do not establish clinical correctness.', '',
        '![Figure 3. Source-stratified retrieval, emission coverage and the paired semantic-alignment cost of withholding the same draft.](output/research/figures/rag_expanded_results.png)']
    section('### 7.3 Generation, verification and coverage','### 7.4 Model-based semantic and usability proxies','\n'.join(alignment))
    with (DATA/'tables/judge_by_guideline.csv').open(encoding='utf8') as fobj:
        judges=list(csv.DictReader(fobj))
    judge=['Table 8. Dependent model-judge means with judged-output coverage. These are automated proxies rather than clinician usability observations.', '',
        '| Guideline | Arm | Judged / quality N | Grounding | Fidelity | Completeness | Actionability | Uncertainty | Unsafe claims |','| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for g in counts:
        for arm in ['without_verification','with_verification']:
            rows={r['metric']:r for r in judges if r['guideline']==g and r['arm']==arm}
            a=rows['grounding']
            vals=[f(float(rows[k]['mean'])) if rows[k]['mean'] else 'NA' for k in ['grounding','patient_fidelity','completeness','actionability','uncertainty']]
            judge.append(f'| {g} | {arm.replace("_"," ")} | {a["judge_n"]}/{a["quality_n"]} | '+' | '.join(vals)+f' | {rows["unsafe_claim_count"]["observed_sum"]} |')
    judge+=['','The same model supplies generation, audit and judge roles. Released-only judge means describe a selected subset, and shared-model agreement does not establish independent clinical correctness. Completed invalid judge outputs remain unavailable ratings rather than favorable imputations. Source-specific intervals and rating denominators are retained in the CSV tables.']
    section('### 7.4 Model-based semantic and usability proxies','### 7.5 Injected faults, failure cases and runtime','\n'.join(judge))
    faults=['Table 9. Deliberately injected errors, separated by guideline; invalid verdicts are not credited as semantic detection.', '',
        '| Guideline | Injected | Unverified emitted | Verified emitted | Structural reject | Semantic reject | Invalid verdict |','| --- | --- | --- | --- | --- | --- | --- |']
    for r in summary['faults']:
        faults.append(f'| {r["guideline"]} | {r["quality_n"]} | {r["unverified_released"]} | {r["verified_released"]} | {r["structural_rejection"]} | {r["semantic_rejection"]} | {r["invalid_review"]} |')
    faults+=['','These 36 intentionally enriched drafts test negation reversal, missing conditions, invented doses and fabricated normal findings. Counts are not estimates of naturally occurring hallucination prevalence. Per-case and fault-family bootstrap contrasts are provided in the CSV tables.', '',
        'Latency is not treated as a quality result because operational wall time includes minute-rate waits and checkpoint replay. Provider outages are retained in operational logs and excluded from quality populations; completed malformed answers and clinical disagreement remain outcomes.']
    section('### 7.5 Injected faults, failure cases and runtime','## 8. Discussion and limitations','\n'.join(faults))
    old_lim='The RAG fixture is small, synthetic, English-language and based on one guideline extraction. References were written by the engineering workflow, and repeated variants share templates. The same cases informed the quote-ID refinement, preventing an untouched-test interpretation.'
    new_lim='The RAG fixture contains 100 synthetic English-language cases across NICE, AAP and WHO rather than an external patient cohort. References and gold passages were proposed by the engineering workflow, repeated variants share templates and clinical adjudication remains pending. The original 18 cases informed earlier quote-ID development; a superseded retrieval-only expansion also preceded the user-requested size amendment, preventing an untouched-test interpretation. Different guideline populations, recommendation styles and candidate-pool sizes limit cross-source comparisons. WHO covers 0-59-day infections and resource-dependent referral pathways, while only its first-72-hour subset is tested; AAP cases remain within the at-least-35-week report.'
    assert old_lim in text
    text=text.replace(old_lim,new_lim)
    text=text.replace('concept expansion does not improve this benchmark.','concept expansion has lower measured Recall@4 than hybrid retrieval in each source-specific cohort.')
    text=text.replace('The measured clinical retrieval results in Section 7 remain those of the frozen earlier experiment and are not attributed to these unbenchmarked refinements.',
        'The synthetic retrieval results in Section 7 use the frozen broad-concept evaluation configuration and are not measurements of these additional production refinements.')
    text=text.replace('the numerical retrieval results in Section 7 remain those of the frozen earlier experiment and are not attributed to these unbenchmarked refinements.',
        'the synthetic retrieval results in Section 7 use the frozen broad-concept evaluation configuration and do not measure these additional production refinements.')
    bounded=['The same 100 cases are evaluated with the two original additional Groq backbones. Each one-revision arm reuses its paired initial draft and completed audits, including malformed output and dissent. At most one revision is permitted after completed disagreement; both auditors freshly assess any revision. The original 120-second budget and 20-second minimum cloud-call gap are retained, with initial elapsed time deducted during replay. The primary paired experiment remains a zero-repair release-filtering study.', '',
        'Table 12. Source-stratified bounded-resolution release counts and paired release-fraction differences.', '',
        '| Backbone | Guideline | Paired N | Baseline released | One-repair arm released | Attempts | Difference | Case 95% CI | Family 95% CI |','| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in summary['resolution']:
        bounded.append(f'| {r["model"]} | {r["guideline"]} | {r["paired_n"]} | {r["no_repair_released"]} | {r["one_repair_released"]} | {r["resolution_attempts"]} | {f(r["mean"])} | {interval(r)} | {interval(r,"family")} |')
    bounded+=['','Release is an engineering gate, not a clinical correctness label. Models audit their own backbone outputs, elapsed-time constraints can prevent resolution, and the synthetic fixtures do not establish independent expert acceptance. The existing budget is a preflight admission condition rather than a hard wall-clock deadline; provider waits can exceed it. Source code, settings, role responses and revision traces remain archived. The deployed schema-enforced application is distinct from these fixed JSON-object research runs.']
    integration=old[old.index('After these frozen JSON-object experiments,'):old.index('## 12. Frozen ten-case pilot')].strip()
    bounded+=['',integration.replace('After these frozen JSON-object experiments,','After the historical JSON-object experiments,')]
    section('### 11.4 Additional backbones and bounded resolution','## 12. Frozen ten-case pilot and saturated-score investigation','\n'.join(bounded))
    replacements={
        'We present NeoGuard EOS, a clinician-facing research application':'NeoGuard EOS is a clinician-facing research application',
        'We evaluate supplied-label classification':'The study evaluates supplied-label classification',
        'We report lexical and semantic alignment together with abstention coverage, rather than equating text similarity or selective release with clinical correctness.':'Lexical and semantic alignment are reported together with abstention coverage, rather than equating text similarity or selective release with clinical correctness.',
        'We adapt that general design idea to serial neonatal observations, without reusing its EEG data, reference reports or numerical findings.':'That general design idea is adapted to serial neonatal observations, without reusing its EEG data, reference reports or numerical findings.',
        'Our representation contains':'The representation contains',
        'We therefore pair them with source checks, a fallible model-based judge and deliberate fault injection.':'These metrics are therefore paired with source checks, a fallible model-based judge and deliberate fault injection.'}
    for a,b in replacements.items():
        text=text.replace(a,b)
    prose=text.split('## References',1)[0]
    remaining=list(re.finditer(r'\b(we|our)\b',prose,re.I))
    assert not remaining,'First-person wording remains: '+repr([text[max(0,m.start()-50):m.end()+80] for m in remaining])
    revision=ROOT/'tmp/expanded100-paper-preview' if preview else DATA/'paper_revision'
    revision.mkdir(exist_ok=True)
    # Include every changed sentence plus changed table/caption lines. Added and
    # deleted sentences are explicit, not hidden behind a section-level note.
    def units(value):
        result=[]
        for line in value.splitlines():
            if not line.strip():continue
            result.extend(re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])',line))
        return result
    before,after=units(old),units(text)
    changes=[]
    for op,a,b,c,d in difflib.SequenceMatcher(a=before,b=after,autojunk=False).get_opcodes():
        if op=='equal':continue
        for left,right in itertools.zip_longest(before[a:b],after[c:d],fillvalue=''):
            number_pattern=r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:/\d+)?%?'
            changes.append({'change_id':len(changes)+1,'operation':op,'old_sentence_or_table_line':left,'new_sentence_or_table_line':right,
                'old_number_literals':json.dumps(re.findall(number_pattern,left)),
                'new_number_literals':json.dumps(re.findall(number_pattern,right))})
    with (revision/'sentence_changes.csv').open('w',newline='',encoding='utf8') as fobj:
        writer=csv.DictWriter(fobj,fieldnames=list(changes[0]));writer.writeheader();writer.writerows(changes)
    (revision/'sentence_changes.md').write_text('# Sentence and table change log\n\n'+ '\n\n'.join(f'## {r["change_id"]}\n\nOld: {r["old_sentence_or_table_line"] or "[added]"}\n\nNew: {r["new_sentence_or_table_line"] or "[deleted]"}' for r in changes)+'\n',encoding='utf8')
    (revision/'manuscript_before.md').write_text(old,encoding='utf8')
    (revision/'manuscript_after.md').write_text(text,encoding='utf8')
    plot_results(summary)
    target=revision/'manuscript.md' if preview else SOURCE
    target.write_text(text,encoding='utf8')
    print({'changed_sentences_and_table_lines':len(changes),'manuscript':str(target),'preview':preview,'pdf_render_required':True})

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--preview',action='store_true')
    main(parser.parse_args().preview)
