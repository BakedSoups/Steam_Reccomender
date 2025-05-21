# first lets get a list of all metacritic games

# compare it to steam_api list

# we should be able to have context of previous games if the review is mentioning it and build tags from that 

import requests
from datetime import datetime

def gather_steam_reviews(appid: int, count: int = 100)-> list: 

    url = f"https://store.steampowered.com/appreviews/{appid}" 

    params = { 
        "json" :1, 
        "num_per_page": count, 
        "filter":"recent",
        "language": "english"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "reviews" not in data: 
        raise Exception("No reviews in this game")
    reviews = []
    for review in data["reviews"]:
        reviews.append({
            "author_id": review["author"]["steamid"],
            "review": review["review"],
            "voted_up": review["voted_up"],
            "playtime_hours": round(review["author"]["playtime_forever"] / 60, 1),
            "date": datetime.fromtimestamp(review["timestamp_created"]).isoformat()
        })

    return reviews

if __name__ == "__main__":
    appid = 570  # dota 2
    reviews = gather_steam_reviews(appid, 20)
    for i, r in enumerate(reviews, 1):
        if len(r['review'])> 100:
            print(f"{i}. ({r['date']}) upvoted: {r['voted_up']} | {r['playtime_hours']} hrs\n{r['review']}\n")
        else: 

            print("not a insightful review")