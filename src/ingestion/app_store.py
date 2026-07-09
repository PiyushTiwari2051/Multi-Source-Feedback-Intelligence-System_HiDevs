import logging
import requests
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def fetch_app_store_reviews(app_id: str, pages: int = 1) -> List[Dict[str, Any]]:
    """
    Fetches reviews for an App Store app using the iTunes RSS JSON feed.
    Returns normalized reviews matching the schema:
    {id, source, text, rating, date, raw}
    """
    logger.info(f"Fetching App Store reviews for App ID {app_id} (pages: {pages})")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'
    }
    
    normalized_reviews = []
    
    # Cap pages at 10 (iTunes RSS limit)
    pages = min(max(1, pages), 10)
    
    for page in range(1, pages + 1):
        url = f"https://itunes.apple.com/us/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch App Store reviews page {page}: Status code {response.status_code}")
                continue
                
            data = response.json()
            feed = data.get('feed', {})
            entries = feed.get('entry', [])
            
            if not entries:
                logger.info(f"No more entries found on page {page}.")
                break
                
            # If there is only one entry, it might be returned as a dict instead of a list
            if isinstance(entries, dict):
                entries = [entries]
                
            for entry in entries:
                # Skip the first entry if it's the app information (doesn't have rating)
                if 'im:rating' not in entry:
                    continue
                    
                review_id = entry.get('id', {}).get('label')
                rating_str = entry.get('im:rating', {}).get('label')
                title = entry.get('title', {}).get('label', '')
                content = entry.get('content', {}).get('label', '')
                updated_str = entry.get('updated', {}).get('label')
                
                # Combine title and content
                text = f"{title}\n{content}".strip() if title else content.strip()
                
                # Parse date
                # Format is typically ISO 8601: "2023-05-15T09:00:00-07:00"
                if not updated_str:
                    updated_str = datetime.utcnow().isoformat()
                
                normalized_reviews.append({
                    'id': f"as_{review_id}" if review_id else None,
                    'source': 'app_store',
                    'text': text,
                    'rating': int(rating_str) if rating_str else None,
                    'date': updated_str,
                    'raw': str(entry)
                })
                
        except Exception as e:
            logger.error(f"Error fetching page {page} of App Store reviews: {e}", exc_info=True)
            
    # Deduplicate and filter out entries without an ID
    seen_ids = set()
    unique_reviews = []
    for r in normalized_reviews:
        if r['id'] and r['id'] not in seen_ids:
            seen_ids.add(r['id'])
            unique_reviews.append(r)
            
    logger.info(f"Successfully fetched {len(unique_reviews)} reviews from App Store.")
    return unique_reviews
