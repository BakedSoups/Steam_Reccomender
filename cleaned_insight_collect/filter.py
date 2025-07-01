from sentiment_analysis import analyze_review_sentiment
from keyword_frequency_analysis import count_review_keywords, has_ascii_art

def filter_handler(review, length, ideal_sentiment, expected_keywords): 
    if len(review) < length: 
        return False, {}
    
    sentiment_score = analyze_review_sentiment(review)

    if not(sentiment_score['compound'] > ideal_sentiment and sentiment_score['confidence'] > .5): 
       return False, {}
    
    keyword_frequencies = count_review_keywords(review)
    
    
    if sum(keyword_frequencies.values()) < expected_keywords: 
       return False, {}
    
    
    return True, keyword_frequencies
    
