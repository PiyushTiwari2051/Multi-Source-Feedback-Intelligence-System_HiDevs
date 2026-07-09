import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

VALID_CATEGORIES = ['Bug', 'Crash', 'Feature Request', 'Support', 'Pricing', 'Other']

def calculate_priority_scores(reviews: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Calculates priority scores and levels per category.
    Priority Score = category_frequency * average_negativity_in_category
    where:
      - negativity of a review = sentiment_score if sentiment_label == 'negative' else 0.0
      - average_negativity_in_category = sum(negativity) / category_frequency
      
    Returns a dict mapping category name to a dict of analysis:
    {
        'score': float,
        'level': 'High' | 'Medium' | 'Low',
        'frequency': int,
        'avg_negativity': float
    }
    """
    # Initialize counts
    category_data = {
        cat: {'negativity_sum': 0.0, 'frequency': 0, 'negative_count': 0}
        for cat in VALID_CATEGORIES
    }
    
    for r in reviews:
        cat = r.get('category')
        if cat not in category_data:
            cat = 'Other'
            
        category_data[cat]['frequency'] += 1
        
        # Calculate negativity score (only negative sentiment contributes)
        if r.get('sentiment_label') == 'negative':
            score = r.get('sentiment_score', 0.0)
            category_data[cat]['negativity_sum'] += score
            category_data[cat]['negative_count'] += 1

    results = {}
    for cat in VALID_CATEGORIES:
        data = category_data[cat]
        freq = data['frequency']
        neg_sum = data['negativity_sum']
        neg_count = data['negative_count']
        
        avg_negativity = neg_sum / freq if freq > 0 else 0.0
        
        # Priority Score = frequency * avg_negativity = neg_sum
        priority_score = round(neg_sum, 4)
        
        # Assign Priority Level
        # Standard Rules:
        # - Crash with any negative review is automatically High
        # - Bug with score >= 1.5 is High
        # - Any category with priority score >= 3.0 is High
        # - Score between 0.5 and 3.0 is Medium
        # - Score < 0.5 is Low
        if cat == 'Crash' and neg_count >= 1:
            level = 'High'
        elif cat == 'Bug' and priority_score >= 1.5:
            level = 'High'
        elif priority_score >= 3.0:
            level = 'High'
        elif priority_score >= 0.5:
            level = 'Medium'
        else:
            level = 'Low'
            
        results[cat] = {
            'score': priority_score,
            'level': level,
            'frequency': freq,
            'avg_negativity': round(avg_negativity, 4)
        }
        
    return results
