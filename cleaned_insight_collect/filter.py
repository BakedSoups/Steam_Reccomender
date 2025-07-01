from sentiment_analysis import analyze_review_sentiment


def filter_handler(review, length, sentiment): 
    if len(review) < length: 
        return False
    return True