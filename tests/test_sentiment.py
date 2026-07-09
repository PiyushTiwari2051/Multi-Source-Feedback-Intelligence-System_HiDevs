import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.processing.sentiment import analyze_sentiment

def test_positive_sentiment():
    text = "This is an absolutely amazing app! Highly recommended and works perfectly."
    res = analyze_sentiment(text)
    assert res['label'] == 'positive'
    assert res['score'] > 0.5
    assert res['compound'] > 0.5

def test_negative_sentiment():
    text = "Horrible app. It crashes constantly and has terrible customer support. Do not download!"
    res = analyze_sentiment(text)
    assert res['label'] == 'negative'
    assert res['score'] > 0.5
    assert res['compound'] < -0.5

def test_neutral_sentiment():
    # Simple neutral statement
    text = "I opened the app and logged in to check my account balances."
    res = analyze_sentiment(text)
    assert res['label'] == 'neutral'
    # For neutral, score is 1 - abs(compound)
    assert res['score'] > 0.8
    assert abs(res['compound']) < 0.05

def test_empty_sentiment():
    res = analyze_sentiment("")
    assert res['label'] == 'neutral'
    assert res['score'] == 1.0
    assert res['compound'] == 0.0
