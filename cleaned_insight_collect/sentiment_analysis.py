"""
VADER Sentiment Analysis for Steam Reviews
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize the analyzer
analyzer = SentimentIntensityAnalyzer()


def analyze_review_sentiment(review_text: str) -> dict:
    """
    Analyze sentiment of a single review using VADER
    
    Args:
        review_text (str): The review text to analyze
        
    Returns:
        dict: Sentiment scores and classification
    """
    # Get VADER scores
    scores = analyzer.polarity_scores(review_text)
    
    # Classify overall sentiment
    compound = scores['compound']
    return {
        'compound': compound,          
        'confidence': abs(compound)   
    }



# Example usage and testing
if __name__ == "__main__":
    # Test with sample review texts
    sample_reviews = [
        "This game is absolutely amazing! I love everything about it.",
        "Terrible game, waste of money. Very disappointed.",
        "It's okay, nothing special but not bad either.",
        "BEST GAME EVER!!! 10/10 would recommend to everyone!",
        "Buggy mess, developers don't care about players.",
        "Pretty good game with some minor issues.",
        "yabba gabba gabba goo ***D(()Q#*R)*@)(#)"
    ]
    
    print("VADER Sentiment Analysis Test")
    print("=" * 50)
    
    for i, text in enumerate(sample_reviews, 1):
        print(text)
        print(analyze_review_sentiment(text))         

    