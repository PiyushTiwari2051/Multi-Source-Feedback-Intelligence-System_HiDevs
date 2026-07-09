import pandas as pd
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def calculate_trends(reviews: List[Dict[str, Any]], interval: str = 'daily') -> pd.DataFrame:
    """
    Groups reviews by date interval and calculates counts of positive, neutral, and negative sentiment.
    Returns a DataFrame with columns: ['date', 'positive', 'neutral', 'negative', 'total_volume', 'avg_rating']
    """
    if not reviews:
        return pd.DataFrame(columns=['date', 'positive', 'neutral', 'negative', 'total_volume', 'avg_rating'])
        
    try:
        df = pd.DataFrame(reviews)
        # Parse reviews dates
        df['date_parsed'] = pd.to_datetime(df['date'], format='ISO8601', errors='coerce', utc=True)
        
        # Drop rows with unparseable dates
        df = df.dropna(subset=['date_parsed'])
        
        if df.empty:
            return pd.DataFrame(columns=['date', 'positive', 'neutral', 'negative', 'total_volume', 'avg_rating'])
            
        if interval == 'weekly':
            # Group by week starting Monday
            df['interval_date'] = df['date_parsed'].dt.to_period('W').dt.start_time
        else:
            # Group by day
            df['interval_date'] = df['date_parsed'].dt.date
            
        # Group by interval_date
        grouped = df.groupby('interval_date')
        
        trend_data = []
        for date_val, group in grouped:
            counts = group['sentiment_label'].value_counts()
            total = len(group)
            
            # Safe calculation of average rating
            ratings = group['rating'].dropna()
            avg_rating = float(ratings.mean()) if not ratings.empty else None
            
            # Ensure date_val is formatted as string or date object
            date_str = str(date_val)
            
            trend_data.append({
                'date': date_str,
                'positive': int(counts.get('positive', 0)),
                'neutral': int(counts.get('neutral', 0)),
                'negative': int(counts.get('negative', 0)),
                'total_volume': total,
                'avg_rating': avg_rating
            })
            
        trend_df = pd.DataFrame(trend_data)
        # Sort chronologically
        trend_df = trend_df.sort_values('date')
        return trend_df
        
    except Exception as e:
        logger.error(f"Error calculating trends: {e}", exc_info=True)
        return pd.DataFrame(columns=['date', 'positive', 'neutral', 'negative', 'total_volume', 'avg_rating'])
