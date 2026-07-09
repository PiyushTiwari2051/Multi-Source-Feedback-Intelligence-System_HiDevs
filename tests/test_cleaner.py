import sys
import os

# Ensure project path is accessible
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.processing.cleaner import clean_text

def test_clean_html_tags():
    raw = "Hello <b>world</b>! This is a <a href='#'>link</a>."
    expected = "Hello world! This is a link."
    assert clean_text(raw) == expected

def test_clean_urls():
    raw = "Check out https://google.com for info. Or visit www.apple.com"
    expected = "Check out for info. Or visit"
    assert clean_text(raw) == expected

def test_normalize_whitespace():
    raw = "  Hello \n \t world!   Too   many   spaces.  "
    expected = "Hello world! Too many spaces."
    assert clean_text(raw) == expected

def test_html_unescaping():
    raw = "Reviews &amp; Ratings &lt; 5 stars"
    expected = "Reviews & Ratings < 5 stars"
    assert clean_text(raw) == expected

def test_non_string_input():
    assert clean_text(None) == ""
    assert clean_text(123) == ""
