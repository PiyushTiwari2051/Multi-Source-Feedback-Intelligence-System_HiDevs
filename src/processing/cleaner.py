import re
import html

def clean_text(text: str) -> str:
    """
    Cleans raw review text by unescaping HTML entities, removing HTML tags,
    stripping URLs, and normalizing whitespaces.
    """
    if not isinstance(text, str):
        return ""
        
    # Unescape HTML characters (e.g. &amp; -> &)
    cleaned = html.unescape(text)
    
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]*>', '', cleaned)
    
    # Remove URLs/hyperlinks
    cleaned = re.sub(r'https?://\S+|www\.\S+', '', cleaned)
    
    # Normalize whitespace (replace multiple spaces/tabs/newlines with a single space)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned.strip()
