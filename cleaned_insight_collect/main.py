from steam_extract import get_steam_reviews
from sentiment_analysis import analyze_review_sentiment
import filter 

# Method 2: Direct function call
reviews = get_steam_reviews(appid=730, count=100)

if reviews:
    print(reviews[1])
    for review in reviews:
        if filter.filter_handler(review, 90): 
            print(review)
        