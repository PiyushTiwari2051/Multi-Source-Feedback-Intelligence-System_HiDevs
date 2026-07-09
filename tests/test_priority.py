import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.intelligence.priority import calculate_priority_scores

def test_empty_priorities():
    res = calculate_priority_scores([])
    for cat in ['Bug', 'Crash', 'Feature Request', 'Support', 'Pricing', 'Other']:
        assert res[cat]['score'] == 0.0
        assert res[cat]['level'] == 'Low'
        assert res[cat]['frequency'] == 0

def test_crash_auto_escalation():
    # If Crash has at least one negative review, it escalates to High
    reviews = [
        {
            'category': 'Crash',
            'sentiment_label': 'negative',
            'sentiment_score': 0.8
        }
    ]
    res = calculate_priority_scores(reviews)
    assert res['Crash']['score'] == 0.8
    assert res['Crash']['level'] == 'High'
    assert res['Crash']['frequency'] == 1

def test_bug_threshold_escalation():
    # If Bug has priority_score >= 1.5, it escalates to High
    reviews = [
        {'category': 'Bug', 'sentiment_label': 'negative', 'sentiment_score': 0.9},
        {'category': 'Bug', 'sentiment_label': 'negative', 'sentiment_score': 0.8}
    ]
    res = calculate_priority_scores(reviews)
    assert res['Bug']['score'] == 1.7
    assert res['Bug']['level'] == 'High'

def test_low_priority_items():
    # If priority score is low (< 0.5), it should be Low
    reviews = [
        {'category': 'Pricing', 'sentiment_label': 'negative', 'sentiment_score': 0.2}
    ]
    res = calculate_priority_scores(reviews)
    assert res['Pricing']['score'] == 0.2
    assert res['Pricing']['level'] == 'Low'
