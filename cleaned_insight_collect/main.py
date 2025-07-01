from steam_extract import get_steam_reviews
import filter 

reviews = get_steam_reviews(appid=893180, count=1000)

print(len(reviews))
if reviews:
    passed_reviews = []
    for review in reviews:
        text = review['review']
        passed, keywords = filter.filter_handler(text, 400, .8, 6)

        if passed: 
            print(f"review:{text}\nword freq: {keywords}") 
            passed_reviews.append({ 
                'text': text, 
                'keywords': keywords, 
            })
        passed_reviews.sort(key=lambda x: x['keywords'].get('total_keywords', 0), reverse=True)
print("\n=== SORTED BY TOTAL KEYWORDS ===")
for i, review_data in enumerate(passed_reviews, 1):
    total_count = review_data['keywords'].get('total_keywords', 0)
    print(f"Rank {i}: {total_count} total keywords")
    print(f"Keywords breakdown: {review_data['keywords']}")
    print(f"Review: {review_data['text'][:550]}...")
    print("-" * 50)