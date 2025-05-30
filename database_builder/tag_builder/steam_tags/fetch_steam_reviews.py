## this creates steam_games_sample_with_reviews.json

import re
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

# Keywords indicating descriptive reviews
KEYWORDS = [
    # gameplay
    "gameplay", "mechanics", "controls", "combat", "story", "graphics", "soundtrack",
    "immersion", "progression", "boss", "difficulty", "pace", "balance", "quest",
    # descriptive words
    "charming"
]
# If the keywords lower case or upper case it doesnt matter
KEYWORD_PATTERN = re.compile(r'\b(' + '|'.join(KEYWORDS) + r')\b', re.IGNORECASE)

SAMPLE_SIZE = 10

# Spam filter patterns
SPAM_PATTERN = re.compile(r"(free key|giveaway|visit my channel|https?://|check my profile)", re.IGNORECASE)

def fetch_reviews(appid: int, num_reviews: int = 500) -> list:
    reviews = []
    cursor = "*"
    while len(reviews) < num_reviews:
        url = f"https://store.steampowered.com/appreviews/{appid}?json=1&filter=recent&language=english&num_per_page=100&cursor={cursor}"
        response = requests.get(url)
        if not response.ok:
            break
        data = response.json()
        new_reviews = data.get("reviews", [])
        reviews.extend(new_reviews)
        if not data.get("cursor") or not new_reviews:
            break
        cursor = data["cursor"]
    return reviews

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
    
    return True


def get_top_descriptive_reviews(appid: int) -> list:
    raw_reviews = fetch_reviews(appid)
    valid_reviews = []

    for review in raw_reviews:
        text = review.get("review", "")

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

