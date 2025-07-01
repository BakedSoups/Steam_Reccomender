from steam_extract import get_steam_reviews
import filter 

reviews = get_steam_reviews(appid=730, count=500)
print(len(reviews))
if reviews:
    for review in reviews:
        text = review['review']
        passed, keywords = filter.filter_handler(text, 400, .7)

        if passed: 
            print(f"review: {text}\nword freq: {keywords}")
