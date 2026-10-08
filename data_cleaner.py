import re
from dateutil import parser as date_parser

def clean_text(text):
    """
    Cleans extracted text by:
    1. Removing all hidden HTML entities (e.g., &nbsp;, &amp;) if parsing missed them.
    2. Squashing multiple spaces, tabs, and newlines into a single space (or newline if meant to be block).
    3. Stripping leading/trailing whitespace.
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Replace common HTML entities that might have slipped through
    entities = {
        '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>', 
        '&quot;': '"', '&apos;': "'", '&#39;': "'"
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)
        
    # Remove non-printable characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Squash whitespace but optionally preserve deliberate newlines if needed,
    # Here we aggressively squash everything to single space for clean CSVs
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_date(date_str):
    """
    Attempts to parse a random date string into a standard ISO 8601 YYYY-MM-DD string.
    Returns original string if parsing fails.
    """
    if not date_str or not isinstance(date_str, str):
        return date_str
        
    try:
        # fuzzy=True ignores non-date words (e.g. "Published on October 1st, 2023")
        dt = date_parser.parse(date_str, fuzzy=True)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OverflowError):
        return date_str

def sanitize_dataframe(df):
    """
    Applies aggressive cleaning to an entire pandas DataFrame.
    """
    for col in df.columns:
        if df[col].dtype == 'object' or df[col].dtype.name == 'string':
            # Clean text
            df[col] = df[col].apply(lambda x: clean_text(x) if isinstance(x, str) else x)
            
            # If the column seems to contain dates, try to parse them
            if any(kw in col.lower() for kw in ['date', 'time', 'created', 'updated']):
                df[col] = df[col].apply(lambda x: parse_date(x) if isinstance(x, str) else x)
    return df
