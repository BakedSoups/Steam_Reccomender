from steam_extract import get_steam_reviews, get_steam_tags, EndpointHandler
from tag_builder import create_profile
import filter 


handler = EndpointHandler(appid=1599600)

# Use the handler methods (no need to pass appid again)
reviews = handler.gather_steam_reviews(count=1000)
official_tags = handler.get_steam_tags()

# Catch all Steam Tags
steam_tags = ', '.join([tag['name'] for tag in official_tags])

# Catch all insightful reviews 
if reviews:
    passed_reviews = []
    for review in reviews:
        if review['voted_up'] == False: 
            pass
        text = review['review']
        # adjust this for tweaking the most ideal review
        passed, keywords = filter.filter_handler(text, 400, .8, 6)
        
        if passed: 
            passed_reviews.append({ 
                'text': text, 
                'keywords': keywords, 
            })

    passed_reviews.sort(key=lambda x: x['keywords'].get('reviewer', 0), reverse=True)
    top_5_reviews = passed_reviews[:5]
    all_review_text = "\n\n".join([review_data['text'] for review_data in top_5_reviews])

if all_review_text: 
    print(f"feeding steam tags: {steam_tags}\n")
    profile = create_profile(all_review_text, steam_tags)
    print(profile)