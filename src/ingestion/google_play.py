import logging
from typing import List, Dict, Any
from google_play_scraper import reviews, Sort

logger = logging.getLogger(__name__)

def fetch_google_play_reviews(app_id: str, count: int = 100) -> List[Dict[str, Any]]:
    """
    Fetches reviews for a given Google Play app ID.
    Returns normalized reviews matching the schema:
    {id, source, text, rating, date, raw}
    """
    logger.info(f"Fetching {count} Google Play reviews for {app_id}")
    try:
        results, _ = reviews(
            app_id,
            lang='en',
            country='us',
            sort=Sort.NEWEST,
            count=count
        )
        
        normalized_reviews = []
        for r in results:
            # Safely handle the date
            date_str = r['at'].isoformat() if hasattr(r['at'], 'isoformat') else str(r['at'])
            
            normalized_reviews.append({
                'id': f"gp_{r['reviewId']}",
                'source': 'google_play',
                'text': r['content'] or "",
                'rating': int(r['score']) if r['score'] is not None else None,
                'date': date_str,
                'raw': str(r)
            })
        
        logger.info(f"Successfully fetched {len(normalized_reviews)} reviews from Google Play.")
        return normalized_reviews
    except Exception as e:
        logger.error(f"Failed to fetch Google Play reviews for {app_id}: {e}", exc_info=True)
        return []
