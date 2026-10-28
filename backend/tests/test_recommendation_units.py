from rag.recommendation_units import extract_nice_units


def test_boxes_do_not_contaminate_recommendations_and_continue_across_pages():
    pages = ['1.9.1\nAssess the history. [2021]\n1.9.2\nSee other guidance. [2021]\nBox 1: Risk factors\n• first factor',
             '1.10 Assessment after birth\n1.10.1\nAssess the infant. [2021]\nBox 2: Indicators\n• first indicator',
             '• continued indicator\n1.10.2\nUse the framework. [2021]\nFor a short explanation see rationale.']
    units, stream = extract_nice_units(pages)
    assert units['NICE-1.9.2']['raw_text'] == 'See other guidance. [2021]'
    assert units['NICE-box1']['raw_text'] == 'Box 1: Risk factors • first factor'
    assert units['NICE-box2']['raw_text'].endswith('• continued indicator')
    assert units['NICE-box2']['pdf_pages'] == [2, 3]
    for unit in units.values():
        span = unit['source_span']
        assert ' '.join(stream[span['start']:span['end']].split()) == unit['raw_text']
    assert units['NICE-1.10.2']['raw_text'] == 'Use the framework. [2021]'
