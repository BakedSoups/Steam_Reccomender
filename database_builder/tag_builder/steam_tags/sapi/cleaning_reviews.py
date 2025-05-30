import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()

KEYWORDS = [
    # gameplay
    "gameplay", "mechanics", "controls", "combat", "story", "graphics", "soundtrack",
    "immersion", "progression", "boss", "difficulty", "pace", "balance", "quest",
    # descriptive words
    "charming"
]

# If the keywords lower case or upper case it doesnt matter
KEYWORD_PATTERN = re.compile(r'\b(' + '|'.join(KEYWORDS) + r')\b', re.IGNORECASE)

SPAM_PATTERN = re.compile(r"(free key|giveaway|visit my channel|https?://|check my profile)", re.IGNORECASE)

ENGLISH_PATTERN = re.compile(r'[a-zA-Z0-9\s\.,!?;:\'"()\-]') 

def count_non_english_letters(text: str) -> int:
    """Count letters that are not in the English alphabet"""
    non_english_chars = ENGLISH_PATTERN.sub('', text)
    non_english_letters = re.findall(r'[^\W\d_]', non_english_chars)
    return len(non_english_letters)

def has_too_many_non_english(text: str, threshold: int = 15) -> bool:
    """Check if text has more than threshold non-English letters"""
    return count_non_english_letters(text) > threshold 

# returns the amount of keywords in reviews
def keyword_score(text: str) -> int:
    keyword_matches = KEYWORD_PATTERN.findall(text)
    return len(keyword_matches)

# if its less than 90 words or is spam we filter it out
def spam(text: str) -> bool:
    if len(text.split()) < 100:
        return False
    if SPAM_PATTERN.search(text):
        return False
    if has_too_many_non_english(text):
            return False
    return True

def filter_descriptve(steam_reviews):
    raw_reviews = steam_reviews
    valid_reviews = []
    for i, review in enumerate(raw_reviews, 1): 
        text = review['review']

        if not spam(text):
            continue
        
        sentiment = analyzer.polarity_scores(text)
        if sentiment["compound"] < 0.3:
            continue

        score = keyword_score(text)
        if score == 0:
            continue

        valid_reviews.append((text, score, sentiment["compound"]))

    sorted_reviews = sorted(valid_reviews, key=lambda x: (x[1], x[2]), reverse=True)
    return sorted_reviews[:5]

