# [{'recommendationid': '195999191', 'author': {'steamid': '76561199741689550', 'num_games_owned': 0, 'num_reviews': 1, 'playtime_forever': 2615, 'playtime_last_two_weeks': 963, 'playtime_at_review': 2606, 'last_played': 1748627170}, 'language': 'english', 'review': 'fuck ths game its full of cheaters', 'timestamp_created': 1748626619, 'timestamp_updated': 1748626619, 'voted_up': False, 'votes_up': 0, 'votes_funny': 0, 'weighted_vote_score': 0.5, 'comment_count': 0, 'steam_purchase': True, 'received_for_free': False, 'written_during_early_access': False, 'primarily_steam_deck': False},
import time

class Steam_Response: 
    def __init__(self): 
        reccomendationid = self.reccomendationid
        reccomendation = self.reccomendation 
        timestamp = self.timestamp 
        playtime_hours = self.playtime_hours
        review = self.review
        votes_up = self.votes_up 
        votes_funny=self.votes_funny 


def clean_missing_values(review): 
    if 'timestamp_created' in review and isinstance(review['timestamp_created'], int):
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(review['timestamp_created']))
    else: 
        timestamp = 0


def print_reviews(reviews_list, num_reviews = None):
  # Handle empty list
    if not reviews_list:
        print("No reviews to display")
        return
    
    # Handle None case (print all)
    if num_reviews is None:
        num_reviews = len(reviews_list)
    
    # Validate num_reviews
    if num_reviews < 0:
        print("Error: Number of reviews cannot be negative")
        return
    if num_reviews > len(reviews_list):
        print(f"Requested {num_reviews} reviews, but only {len(reviews_list)} available")
        return     
    # If num_reviews is 0, don't print anything
    if num_reviews == 0:
        print("No reviews to display (num_reviews = 0)")
        return
    
    # Print the reviews
    reviews_to_print = reviews_list[:num_reviews]
    actual_printed = len(reviews_to_print)

    print(f"==== {actual_printed} Steam Reviews Preview ====")
    print("=" * 60)
    
    for i, review in enumerate(reviews_to_print, 1):
        clean_missing_values
        
        recommendation = "upvote" if review['voted_up'] else "downvote"
        
        playtime_hours = review['author']['playtime_forever'] / 60
        
        print(f"\n--- Review #{i} ---")
        print(f"recommendationid: {review['recommendationid']}")
        print(f"recommendation: {recommendation}")
        print(f"timestamp: {timestamp}")
        print(f"playtime_hours: {playtime_hours:.1f} hours")
        print(f"review: {review['review']}")
        print(f"votes_up: {review['votes_up']}")
        print(f"votes_funny: {review['votes_funny']}")
        print("-" * 40)

