import logging
import nltk
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Ensure NLTK VADER lexicon is downloaded
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    logger.info("VADER lexicon not found. Downloading...")
    try:
        nltk.download('vader_lexicon', quiet=True)
    except Exception as e:
        logger.error(f"Failed to download VADER lexicon: {e}")

from nltk.sentiment.vader import SentimentIntensityAnalyzer

try:
    _analyzer = SentimentIntensityAnalyzer()
except Exception as e:
    logger.critical(f"Failed to initialize VADER SentimentIntensityAnalyzer: {e}")
    _analyzer = None

def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyzes sentiment of text using VADER.
    Returns:
        {
            'label': 'positive' | 'neutral' | 'negative',
            'score': float (confidence score between 0.0 and 1.0),
            'compound': float (raw compound score from -1.0 to 1.0)
        }
    """
    if not text or _analyzer is None:
        return {
            'label': 'neutral',
            'score': 1.0,
            'compound': 0.0
        }
        
    scores = _analyzer.polarity_scores(text)
    compound = scores.get('compound', 0.0)
    
    if compound >= 0.05:
        label = 'positive'
        # Confidence is the magnitude of the compound score
        score = compound
    elif compound <= -0.05:
        label = 'negative'
        score = abs(compound)
    else:
        label = 'neutral'
        # For neutral, confidence is high if compound is close to 0
        score = 1.0 - abs(compound)
        
    # Clamp score to [0.0, 1.0] just in case
    score = max(0.0, min(score, 1.0))
    
    return {
        'label': label,
        'score': round(score, 4),
        'compound': round(compound, 4)
    }
