import time
import requests
   
def get_reviews(appid, num_reviews):
    reviews = []
    cursor = "*"
    while len(reviews) < num_reviews:
        url = f"https://store.steampowered.com/appreviews/{appid}?json=1&filter=recent&language=english&num_per_page=100&cursor={cursor}"
        response = requests.get(url)
        if not response.ok:
            break
        data = response.json()
        new_reviews = data.get("reviews", [])
        reviews.extend(new_reviews)
        if not data.get("cursor") or not new_reviews:
            break
        cursor = data["cursor"]
    # incase the endpoint calls to many reviews
    return reviews[:num_reviews]