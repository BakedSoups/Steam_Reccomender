from steam_extract import get_steam_reviews
import filter 

reviews = get_steam_reviews(appid=730, count=500)
print(len(reviews))
if reviews:
    for review in reviews:
        review = review['review']

        if filter.filter_handler(review, 90, .8): 
