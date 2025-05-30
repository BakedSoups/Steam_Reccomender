import sapi as sp

appid_list = [730, 440]
reviews = sp.get_reviews(appid_list[0], 40)
sp.print_reviews(reviews, 30)
reviews = sp.filter_descriptve(reviews)
print(reviews)
sp.print_reviews(reviews)


    # for i, review in enumerate(reviews_to_print, 1):

#   timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(review['timestamp_created']))
        
#         recommendation = "upvote" if review['voted_up'] else "downvote"
        
#         playtime_hours = review['author']['playtime_forever'] / 60
        
#         print(f"\n--- Review #{i} ---")
#         print(f"recommendationid: {review['recommendationid']}")
#         print(f"recommendation: {recommendation}")
#         print(f"timestamp: {timestamp}")
#         print(f"playtime_hours: {playtime_hours:.1f} hours")
#         print(f"review: {review['review']}")
#         print(f"votes_up: {review['votes_up']}")
#         print(f"votes_funny: {review['votes_funny']}")
#         print("-" * 40)
