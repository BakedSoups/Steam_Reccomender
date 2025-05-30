# [{'recommendationid': '195999191', 'author': {'steamid': '76561199741689550', 'num_games_owned': 0, 'num_reviews': 1, 'playtime_forever': 2615, 'playtime_last_two_weeks': 963, 'playtime_at_review': 2606, 'last_played': 1748627170}, 'language': 'english', 'review': 'fuck ths game its full of cheaters', 'timestamp_created': 1748626619, 'timestamp_updated': 1748626619, 'voted_up': False, 'votes_up': 0, 'votes_funny': 0, 'weighted_vote_score': 0.5, 'comment_count': 0, 'steam_purchase': True, 'received_for_free': False, 'written_during_early_access': False, 'primarily_steam_deck': False},
import time


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
        
    reviews_to_print = reviews_list[:num_reviews] if num_reviews else reviews_list
    
    actual_printed = len(reviews_to_print)

    print(f"==== {actual_printed} Steam Reviews Preview ====")
    print("=" * 60)
    
    for i, review in enumerate(reviews_to_print, 1):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(review['timestamp_created']))
        
        recommendation = "upvote" if review['voted_up'] else "downvote"
        
        playtime_hours = review['author']['playtime_forever'] / 60
        
        print(f"\n--- Review #{i} ---")
        print(f"ID: {review['recommendationid']}")
        print(f"Recommendation: {recommendation}")
        print(f"Date: {timestamp}")
        print(f"Playtime: {playtime_hours:.1f} hours")
        print(f"Review: {review['review']}")
        print(f"Helpful Votes: {review['votes_up']}")
        print(f"Funny Votes: {review['votes_funny']}")
        print("-" * 40)

