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
    if compound >= 0.05:
        sentiment_label = 'positive'
    elif compound <= -0.05:
        sentiment_label = 'negative'
    else:
        sentiment_label = 'neutral'
    
    return {
        'positive': scores['pos'],     # Positive sentiment ratio
        'neutral': scores['neu'],      # Neutral sentiment ratio  
        'negative': scores['neg'],     # Negative sentiment ratio
        'compound': compound,          # Overall sentiment score (-1 to 1)
        'sentiment_label': sentiment_label,
        'confidence': abs(compound)    # How confident we are (0 to 1)
    }


def is_complaint(review_text: str, threshold: float = -0.5) -> bool:
    """
    Check if review is a complaint based on sentiment
    
    Args:
        review_text (str): Review text to analyze
        threshold (float): Compound score threshold for complaints (default: -0.5)
        
    Returns:
        bool: True if review is likely a complaint
    """
    sentiment = analyzer.polarity_scores(review_text)
    return sentiment['compound'] < threshold


def is_highly_positive(review_text: str, threshold: float = 0.6) -> bool:
    """
    Check if review is highly positive
    
    Args:
        review_text (str): Review text to analyze
        threshold (float): Compound score threshold for highly positive (default: 0.6)
        
    Returns:
        bool: True if review is highly positive
    """
    sentiment = analyzer.polarity_scores(review_text)
    return sentiment['compound'] > threshold


def categorize_review_sentiment(review_text: str) -> str:
    """
    Categorize review into detailed sentiment categories
    
    Args:
        review_text (str): Review text to analyze
        
    Returns:
        str: Detailed sentiment category
    """
    scores = analyzer.polarity_scores(review_text)
    compound = scores['compound']
    
    if compound >= 0.8:
        return 'very_positive'
    elif compound >= 0.5:
        return 'positive'
    elif compound >= 0.1:
        return 'slightly_positive'
    elif compound >= -0.1:
        return 'neutral'
    elif compound >= -0.5:
        return 'slightly_negative'
    elif compound >= -0.8:
        return 'negative'
    else:
        return 'very_negative'


def analyze_reviews_batch(reviews: list) -> dict:
    """
    Analyze sentiment for a batch of reviews
    
    Args:
        reviews (list): List of review dictionaries with 'review' key
        
    Returns:
        dict: Aggregate sentiment statistics
    """
    if not reviews:
        return {
            'total_reviews': 0,
            'average_compound': 0,
            'positive_ratio': 0,
            'negative_ratio': 0,
            'neutral_ratio': 0,
            'sentiment_distribution': {}
        }
    
    sentiments = []
    categories = []
    
    for review in reviews:
        review_text = review.get('review', '')
        if review_text:
            sentiment = analyze_review_sentiment(review_text)
            sentiments.append(sentiment)
            categories.append(sentiment['sentiment_label'])
    
    if not sentiments:
        return {
            'total_reviews': len(reviews),
            'average_compound': 0,
            'positive_ratio': 0,
            'negative_ratio': 0,
            'neutral_ratio': 0,
            'sentiment_distribution': {}
        }
    
    # Calculate aggregate statistics
    total = len(sentiments)
    avg_compound = sum(s['compound'] for s in sentiments) / total
    
    positive_count = categories.count('positive')
    negative_count = categories.count('negative')
    neutral_count = categories.count('neutral')
    
    # Detailed sentiment distribution
    detailed_categories = [categorize_review_sentiment(r.get('review', '')) for r in reviews if r.get('review')]
    distribution = {}
    for category in detailed_categories:
        distribution[category] = distribution.get(category, 0) + 1
    
    return {
        'total_reviews': total,
        'average_compound': round(avg_compound, 3),
        'positive_ratio': round(positive_count / total, 3),
        'negative_ratio': round(negative_count / total, 3),
        'neutral_ratio': round(neutral_count / total, 3),
        'sentiment_distribution': distribution
    }


def filter_reviews_by_sentiment(reviews: list, sentiment_type: str = 'positive', 
                               min_confidence: float = 0.1) -> list:

    filtered = []
    
    for review in reviews:
        review_text = review.get('review', '')
        if not review_text:
            continue
            
        sentiment = analyze_review_sentiment(review_text)
        
        if (sentiment['sentiment_label'] == sentiment_type and 
            sentiment['confidence'] >= min_confidence):
            
            # Add sentiment data to review
            review_copy = review.copy()
            review_copy['sentiment_analysis'] = sentiment
            filtered.append(review_copy)
    
    # Sort by confidence (most confident first)
    filtered.sort(key=lambda x: x['sentiment_analysis']['confidence'], reverse=True)
    
    return filtered


# Example usage and testing
if __name__ == "__main__":
    # Test with sample review texts
    sample_reviews = [
        "This game is absolutely amazing! I love everything about it.",
        "Terrible game, waste of money. Very disappointed.",
        "It's okay, nothing special but not bad either.",
        "BEST GAME EVER!!! 10/10 would recommend to everyone!",
        "Buggy mess, developers don't care about players.",
        "Pretty good game with some minor issues."
    ]
    
    print("VADER Sentiment Analysis Test")
    print("=" * 50)
    
    for i, text in enumerate(sample_reviews, 1):
        sentiment = analyze_review_sentiment(text)
        category = categorize_review_sentiment(text)
        
        print(f"\nReview {i}: {text}")
        print(f"Compound Score: {sentiment['compound']:.3f}")
        print(f"Label: {sentiment['sentiment_label']}")
        print(f"Category: {category}")
        print(f"Confidence: {sentiment['confidence']:.3f}")
        print(f"Is Complaint: {is_complaint(text)}")
        print(f"Highly Positive: {is_highly_positive(text)}")
    
    # Test batch analysis
    print(f"\n\nBatch Analysis:")
    print("=" * 30)
    
    review_dicts = [{'review': text} for text in sample_reviews]
    batch_results = analyze_reviews_batch(review_dicts)
    
    print(f"Total Reviews: {batch_results['total_reviews']}")
    print(f"Average Sentiment: {batch_results['average_compound']}")
    print(f"Positive Ratio: {batch_results['positive_ratio']}")
    print(f"Negative Ratio: {batch_results['negative_ratio']}")
    print(f"Neutral Ratio: {batch_results['neutral_ratio']}")
    print(f"Distribution: {batch_results['sentiment_distribution']}")