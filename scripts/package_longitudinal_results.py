"""Package aggregate PIC research only; no restricted rows or model weights."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/research/pic_longitudinal'


def main():
    names=['protocol.json','cohort_audit.json','initial_unit_exclusion_audit.json',
        'training_protocol.json','initial_training_protocol.json','model_comparison.json',
        'model_comparison.csv','operating_points.csv','results.md','validation_status.json']
    files=[BASE/n for n in names]
    files += [BASE/'paper_inspired_bayes'/n for n in ['protocol.json','results.json',
        'metrics.csv','intervals.csv','paired_intervals.csv','fold_counts.csv']]
    nested=BASE/'nested_improvement'
    if (nested/'results.json').exists():
        files += [nested/n for n in ['protocol.json','results.json','metrics.csv','intervals.csv',
            'paired_intervals.csv','inner_selection.csv','inner_scores.csv','positive_event_influence.json',
            'positive_event_influence.csv','report.md']]
        files += [ROOT/'backend/ml/improve_pic_models.py',ROOT/'backend/tests/test_pic_nested_improvement.py']
    files+=[ROOT/'docs/research/pic_longitudinal_model_card.md',ROOT/'docs/research/manuscript.md',
            ROOT/'output/pdf/neoguard-eos-research-paper.pdf']
    files+=sorted((ROOT/'docs/research/linked_cohort_template').glob('*'))
    files+=[ROOT/p for p in ['backend/ml/pic_dataset.py','backend/ml/dynamic_contract.py',
        'backend/ml/dynamic_features.py','backend/ml/train_pic_longitudinal.py',
        'backend/ml/temporal_bayes.py','backend/ml/evaluate_pic_bayes.py',
        'backend/ml/longitudinal_inputs.py','backend/ml/requirements-training.txt']]
    for p in files:
        if not p.is_file() or 'data' in p.relative_to(ROOT).parts or p.name=='dynamic_model.json':
            raise ValueError('Unexpected private or absent research artifact')
    manifest={'stage':'development_only','clinical_ready':False,'restricted_patient_records_included':False,
        'real_data_model_weights_included':False,'files_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    path=BASE/'results_manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n')
    files.append(path);archive=BASE.parent/'neoguard-pic-longitudinal-development.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        if not all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in manifest['files_sha256'].items()):
            raise ValueError('Packaged hash mismatch')
    print(json.dumps({'archive':str(archive),'files':len(files),'restricted_patient_records_included':False}))


if __name__=='__main__':main()
