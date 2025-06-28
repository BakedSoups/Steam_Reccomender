"""
Find the most insightful and descriptive reviews based on keyword frequency, word count, and sentiment
"""

import re
from collections import Counter
from typing import List, Dict
from sentiment_analysis import analyze_review_sentiment


def clean_and_extract_keywords(text: str) -> List[str]:
    """
    Extract meaningful descriptive keywords from text
    
    Args:
        text (str): Review text to analyze
        
    Returns:
        List[str]: List of descriptive keywords
    """
    # Convert to lowercase and clean
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Descriptive keywords we want to prioritize
    descriptive_keywords = {
        # Gameplay descriptors
        'gameplay', 'mechanics', 'controls', 'combat', 'difficulty', 'challenging',
        'smooth', 'responsive', 'intuitive', 'clunky', 'frustrating', 'satisfying',
        
        # Visual descriptors  
        'graphics', 'visuals', 'art', 'style', 'beautiful', 'stunning', 'gorgeous',
        'detailed', 'atmospheric', 'immersive', 'realistic', 'stylized', 'pixelated',
        
        # Audio descriptors
        'sound', 'music', 'soundtrack', 'audio', 'voice', 'effects', 'ambient',
        
        # Story/Content descriptors
        'story', 'plot', 'narrative', 'characters', 'dialogue', 'world', 'lore',
        'engaging', 'compelling', 'interesting', 'boring', 'confusing',
        
        # Quality descriptors
        'polished', 'buggy', 'glitchy', 'optimized', 'performance', 'stable',
        'broken', 'crashes', 'laggy', 'smooth', 'fluid', 'excellent', 'terrible',
        
        # Experience descriptors
        'fun', 'addictive', 'boring', 'repetitive', 'variety', 'replayability',
        'innovative', 'unique', 'original', 'creative', 'generic', 'fresh'
    }
    
    # Common stop words to ignore
    stop_words = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
        'this', 'that', 'with', 'have', 'will', 'they', 'been', 'very', 'really',
        'just', 'like', 'game', 'games', 'play', 'playing', 'played', 'much',
        'good', 'great', 'bad', 'nice', 'best', 'love', 'hate', 'recommend'
    }
    
    words = text.split()
    
    # Extract meaningful words
    keywords = []
    for word in words:
        if (len(word) >= 4 and 
            word not in stop_words and 
            not word.isdigit()):
            keywords.append(word)
    
    # Count descriptive keywords separately
    descriptive_found = [word for word in keywords if word in descriptive_keywords]
    
    return keywords, descriptive_found


def calculate_insight_score(review_text: str) -> Dict:
    """
    Calculate how insightful a review is based on multiple factors
    
    Args:
        review_text (str): Review text to score
        
    Returns:
        Dict: Insight scoring breakdown
    """
    # Get sentiment analysis
    sentiment = analyze_review_sentiment(review_text)
    
    # Extract keywords
    all_keywords, descriptive_keywords = clean_and_extract_keywords(review_text)
    
    # Word count factors
    word_count = len(all_keywords)
    unique_words = len(set(all_keywords))
    descriptive_count = len(descriptive_keywords)
    unique_descriptive = len(set(descriptive_keywords))
    
    # Calculate scores (0-1 scale)
    
    # Length score - prefer substantial reviews (100-500 words ideal)
    if word_count < 50:
        length_score = word_count / 50  # Scale up short reviews
    elif word_count <= 200:
        length_score = 1.0  # Ideal range
    elif word_count <= 500:
        length_score = 1.0 - ((word_count - 200) / 600)  # Slight penalty for very long
    else:
        length_score = 0.3  # Heavy penalty for extremely long reviews
    
    # Descriptive score - how many descriptive keywords
    descriptive_score = min(descriptive_count / 10, 1.0)  # Cap at 1.0
    
    # Diversity score - vocabulary richness
    diversity_score = unique_words / max(word_count, 1) if word_count > 0 else 0
    
    # Specificity score - unique descriptive terms
    specificity_score = unique_descriptive / max(descriptive_count, 1) if descriptive_count > 0 else 0
    
    # Sentiment confidence - how clear the sentiment is
    confidence_score = abs(sentiment['compound'])
    
    # Combined insight score with weights
    insight_score = (
        length_score * 0.25 +           # 25% - adequate length
        descriptive_score * 0.35 +      # 35% - descriptive content
        diversity_score * 0.15 +        # 15% - vocabulary diversity
        specificity_score * 0.15 +      # 15% - specific descriptors
        confidence_score * 0.10         # 10% - clear sentiment
    )
    
    return {
        'insight_score': round(insight_score, 3),
        'word_count': word_count,
        'unique_words': unique_words,
        'descriptive_keywords': descriptive_keywords,
        'unique_descriptive': unique_descriptive,
        'sentiment_confidence': round(confidence_score, 3),
        'sentiment_label': sentiment['sentiment_label'],
        'length_score': round(length_score, 3),
        'descriptive_score': round(descriptive_score, 3),
        'diversity_score': round(diversity_score, 3),
        'specificity_score': round(specificity_score, 3)
    }


def get_most_insightful_reviews(reviews: List[dict], max_reviews: int = 10) -> List[dict]:
    """
    Get the most insightful and descriptive reviews
    
    Args:
        reviews (List[dict]): List of review dictionaries with 'review' key
        max_reviews (int): Maximum number of reviews to return
        
    Returns:
        List[dict]: Most insightful reviews with scoring data
    """
    scored_reviews = []
    
    for review in reviews:
        review_text = review.get('review', '')
        if not review_text or len(review_text.strip()) < 50:  # Skip very short reviews
            continue
        
        # Calculate insight score
        insight_data = calculate_insight_score(review_text)
        
        # Add to scored list
        review_copy = review.copy()
        review_copy['insight_analysis'] = insight_data
        scored_reviews.append(review_copy)
    
    # Sort by insight score (highest first)
    scored_reviews.sort(key=lambda r: r['insight_analysis']['insight_score'], reverse=True)
    
    return scored_reviews[:max_reviews]


def get_keyword_frequency_from_top_reviews(reviews: List[dict], top_n: int = 5) -> Dict[str, int]:
    """
    Get keyword frequency from the most insightful reviews
    
    Args:
        reviews (List[dict]): List of reviews with insight analysis
        top_n (int): Number of top reviews to analyze
        
    Returns:
        Dict[str, int]: Keyword frequency map
    """
    keyword_counter = Counter()
    
    for review in reviews[:top_n]:
        descriptive_keywords = review['insight_analysis']['descriptive_keywords']
        keyword_counter.update(descriptive_keywords)
    
    return dict(keyword_counter.most_common(20))


def analyze_review_insights(reviews: List[dict]) -> Dict:
    """
    Complete analysis of review insights
    
    Args:
        reviews (List[dict]): List of review dictionaries
        
    Returns:
        Dict: Complete insight analysis
    """
    # Get most insightful reviews
    top_reviews = get_most_insightful_reviews(reviews, max_reviews=15)
    
    if not top_reviews:
        return {
            'total_reviews': len(reviews),
            'insightful_reviews': 0,
            'top_keywords': {},
            'insights': []
        }
    
    # Get keyword frequency from top reviews
    top_keywords = get_keyword_frequency_from_top_reviews(top_reviews, top_n=10)
    
    # Prepare insight summaries
    insights = []
    for i, review in enumerate(top_reviews[:10], 1):
        analysis = review['insight_analysis']
        insights.append({
            'rank': i,
            'insight_score': analysis['insight_score'],
            'word_count': analysis['word_count'],
            'descriptive_keywords': analysis['descriptive_keywords'][:5],  # Top 5
            'sentiment': analysis['sentiment_label'],
            'sentiment_confidence': analysis['sentiment_confidence'],
            'review_preview': review['review'][:200] + '...' if len(review['review']) > 200 else review['review'],
            'score_breakdown': {
                'length': analysis['length_score'],
                'descriptive': analysis['descriptive_score'],
                'diversity': analysis['diversity_score'],
                'specificity': analysis['specificity_score']
            }
        })
    
    return {
        'total_reviews': len(reviews),
        'insightful_reviews': len(top_reviews),
        'top_keywords': top_keywords,
        'insights': insights,
        'average_insight_score': round(sum(r['insight_analysis']['insight_score'] for r in top_reviews) / len(top_reviews), 3)
    }


# Example usage and testing
if __name__ == "__main__":
    # Sample reviews for testing
    sample_reviews = [
        {
            'review': "Amazing graphics and smooth gameplay mechanics! The combat system feels very responsive and intuitive. Beautiful art style with stunning atmospheric visuals.",
            'voted_up': True
        },
        {
            'review': "Good game.",
            'voted_up': True
        },
        {
            'review': "The narrative is compelling with well-developed characters and engaging dialogue. The world-building is immersive and detailed. Sound design and soundtrack are excellent, creating a perfect atmospheric experience. Controls are polished and responsive.",
            'voted_up': True
        },
        {
            'review': "Terrible performance issues and buggy gameplay. Graphics look outdated and the story is confusing. Controls are clunky and frustrating. Not optimized well.",
            'voted_up': False
        },
        {
            'review': "Love it so much! Best game ever!",
            'voted_up': True
        }
    ]
    
    print("Most Insightful Reviews Analysis")
    print("=" * 50)
    
    # Analyze insights
    analysis = analyze_review_insights(sample_reviews)
    
    print(f"Total Reviews: {analysis['total_reviews']}")
    print(f"Insightful Reviews Found: {analysis['insightful_reviews']}")
    print(f"Average Insight Score: {analysis['average_insight_score']}")
    print()
    
    print("Top Keywords from Most Insightful Reviews:")
    for keyword, count in list(analysis['top_keywords'].items())[:10]:
        print(f"  {keyword}: {count}")
    print()
    
    print("Most Insightful Reviews (Top 3):")
    for insight in analysis['insights'][:3]:
        print(f"\nRank {insight['rank']} (Score: {insight['insight_score']}):")
        print(f"  Words: {insight['word_count']}, Sentiment: {insight['sentiment']}")
        print(f"  Key descriptors: {', '.join(insight['descriptive_keywords'])}")
        print(f"  Preview: {insight['review_preview']}")
        print(f"  Breakdown: L={insight['score_breakdown']['length']}, D={insight['score_breakdown']['descriptive']}, V={insight['score_breakdown']['diversity']}")