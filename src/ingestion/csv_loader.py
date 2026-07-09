import logging
import pandas as pd
import hashlib
from typing import List, Dict, Any, Union, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def detect_columns(columns: List[str]) -> Dict[str, Optional[str]]:
    """
    Attempts to auto-detect columns for text, rating, and date if mapping is not provided.
    """
    mapping = {'text': None, 'rating': None, 'date': None}
    
    text_keywords = {'text', 'comment', 'review', 'feedback', 'message', 'body'}
    rating_keywords = {'rating', 'score', 'stars', 'grade', 'value'}
    date_keywords = {'date', 'time', 'created', 'timestamp', 'submitted', 'at'}
    
    for col in columns:
        col_lower = col.lower()
        if not mapping['text'] and any(k in col_lower for k in text_keywords):
            mapping['text'] = col
        elif not mapping['rating'] and any(k in col_lower for k in rating_keywords):
            mapping['rating'] = col
        elif not mapping['date'] and any(k in col_lower for k in date_keywords):
            mapping['date'] = col
            
    return mapping

def load_csv_feedback(
    filepath_or_buffer: Any,
    col_mapping: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Loads feedback reviews from a CSV file.
    col_mapping: dictionary mapping {'text': 'csv_col', 'rating': 'csv_col', 'date': 'csv_col'}
    Returns a list of normalized feedback records.
    """
    logger.info("Loading reviews from CSV.")
    try:
        df = pd.read_csv(filepath_or_buffer)
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        return []
        
    # Auto-detect or validate mapping
    detected = detect_columns(list(df.columns))
    
    final_mapping = {}
    if col_mapping:
        final_mapping['text'] = col_mapping.get('text') or detected['text']
        final_mapping['rating'] = col_mapping.get('rating') or detected['rating']
        final_mapping['date'] = col_mapping.get('date') or detected['date']
    else:
        final_mapping = detected
        
    if not final_mapping['text']:
        logger.error("Could not identify the text column in CSV.")
        return []
        
    normalized_reviews = []
    skipped_rows = 0
    
    for idx, row in df.iterrows():
        try:
            text_val = str(row[final_mapping['text']]).strip()
            # Skip empty rows
            if not text_val or text_val.lower() in ('nan', 'null', 'none'):
                skipped_rows += 1
                continue
                
            # Get rating
            rating_val = None
            if final_mapping['rating'] and final_mapping['rating'] in row:
                raw_rating = row[final_mapping['rating']]
                try:
                    if pd.notna(raw_rating):
                        rating_val = int(float(raw_rating))
                except (ValueError, TypeError):
                    pass
            
            # Get date
            date_str = None
            if final_mapping['date'] and final_mapping['date'] in row:
                raw_date = row[final_mapping['date']]
                if pd.notna(raw_date):
                    try:
                        # Try parsing using pandas
                        parsed_date = pd.to_datetime(raw_date)
                        date_str = parsed_date.isoformat()
                    except Exception:
                        date_str = str(raw_date)
            
            if not date_str:
                date_str = datetime.utcnow().isoformat()
                
            # Generate deterministic unique ID
            hash_input = f"{text_val}_{date_str}_{idx}"
            row_id = f"csv_{hashlib.md5(hash_input.encode('utf-8')).hexdigest()[:16]}"
            
            normalized_reviews.append({
                'id': row_id,
                'source': 'csv',
                'text': text_val,
                'rating': rating_val,
                'date': date_str,
                'raw': row.to_json()
            })
        except Exception as row_error:
            skipped_rows += 1
            logger.warning(f"Error parsing row {idx} in CSV: {row_error}")
            
    if skipped_rows > 0:
        logger.info(f"Skipped {skipped_rows} malformed or empty rows in CSV.")
        
    logger.info(f"Successfully loaded {len(normalized_reviews)} records from CSV.")
    return normalized_reviews
