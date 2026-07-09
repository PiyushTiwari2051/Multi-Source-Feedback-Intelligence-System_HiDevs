import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Predefined categories
CATEGORIES = ['Bug', 'Crash', 'Feature Request', 'Support', 'Pricing', 'Other']

# Keyword mappings (lower case)
KEYWORDS = {
    'Crash': [
        'crash', 'freeze', 'force close', 'hang', 'closes', 'crashing', 
        'frozen', 'reboot', 'restart', 'black screen', 'shut down', 'die', 'died'
    ],
    'Bug': [
        'bug', 'error', 'fail', 'glitch', 'broken', 'wrong', 'not working', 
        'doesn\'t work', 'does not work', 'issue', 'problem', 'cannot open', 
        'cant open', 'unable to log', 'login error', 'not loading', 'loads forever', 
        'failed', 'blank screen', 'stuck', 'failure', 'malfunction'
    ],
    'Pricing': [
        'price', 'expensive', 'pay', 'cost', 'free', 'subscription', 'charge', 
        'money', 'ads', 'premium', 'purchase', 'billing', 'buy', 'wallet', 
        'expensive', 'cheap', 'payment', 'transaction', 'robbery', 'scam', 'overpriced'
    ],
    'Support': [
        'help', 'support', 'contact', 'reply', 'email', 'customer service', 
        'no response', 'ticket', 'refund', 'reach out', 'agent', 'operator', 
        'write back', 'answer me'
    ],
    'Feature Request': [
        'feature', 'suggest', 'add', 'request', 'hope to see', 'missing', 
        'please make', 'would love', 'wish', 'want', 'implement', 'update to include', 
        'new option', 'mode', 'improvement', 'better if', 'introduce'
    ]
}

def categorize_by_keywords(text: str) -> str:
    """
    Categorizes feedback text based on rule-based keywords.
    Returns matched category, or 'Other' if no rules match.
    """
    text_lower = text.lower()
    
    # Priority order: Crash -> Bug -> Pricing -> Support -> Feature Request
    for category in ['Crash', 'Bug', 'Pricing', 'Support', 'Feature Request']:
        for keyword in KEYWORDS[category]:
            # Use word boundary or simple search
            if keyword in text_lower:
                return category
                
    return 'Other'

def categorize_by_llm(text: str, api_key: str) -> str:
    """
    Uses Groq API (Llama 3 model) to categorize the feedback text.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = (
        "You are an AI classifier for customer reviews. "
        "Your task is to classify the review into EXACTLY ONE of the following categories: "
        f"{', '.join(CATEGORIES)}. "
        "Do NOT write any explanation or intro. Output ONLY the category name. "
        "Review text: "
    )
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.0,
        "max_tokens": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code == 200:
            result = response.json()
            llm_output = result['choices'][0]['message']['content'].strip()
            
            # Match the LLM output to one of our valid categories
            for cat in CATEGORIES:
                if cat.lower() in llm_output.lower():
                    return cat
            logger.info(f"LLM output '{llm_output}' did not match categories. Defaulting to 'Other'.")
        else:
            logger.warning(f"Groq API returned status code {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error calling Groq API for categorization: {e}")
        
    return 'Other'

def categorize_feedback(text: str) -> str:
    """
    Categorizes feedback using keyword rules first.
    If 'Other' is returned and a GROQ_API_KEY is available, uses Groq Llama 3 as fallback.
    """
    category = categorize_by_keywords(text)
    
    # If the text is classified as 'Other', try LLM fallback
    if category == 'Other':
        api_key = os.getenv("GROQ_API_KEY")
        if api_key and api_key.strip():
            logger.info("Keyword matching returned 'Other'. Querying Groq API for categorization...")
            category = categorize_by_llm(text, api_key)
            
    return category
