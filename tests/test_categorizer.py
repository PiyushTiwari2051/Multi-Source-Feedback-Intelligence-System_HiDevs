import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.processing.categorizer import categorize_feedback

def test_categorize_crash():
    assert categorize_feedback("The app freezes and crashes on login") == "Crash"
    assert categorize_feedback("Force closed immediately upon opening") == "Crash"

def test_categorize_bug():
    assert categorize_feedback("This glitch prevents me from clicking next") == "Bug"
    assert categorize_feedback("The login button is broken and doesn't work") == "Bug"

def test_categorize_pricing():
    assert categorize_feedback("Subscription cost is way too expensive") == "Pricing"
    assert categorize_feedback("I need a refund") == "Support"
    assert categorize_feedback("Too many ads in the free version") == "Pricing"

def test_categorize_support():
    assert categorize_feedback("Please help me contact customer service") == "Support"
    assert categorize_feedback("I emailed support but got no response") == "Support"

def test_categorize_feature_request():
    assert categorize_feedback("Would love to see a dark mode feature") == "Feature Request"
    assert categorize_feedback("Suggest adding an export option") == "Feature Request"

def test_categorize_other():
    # If no key is set and no keywords match, it falls back to Other
    os.environ["GROQ_API_KEY"] = ""
    assert categorize_feedback("Just some random feedback about my day.") == "Other"
