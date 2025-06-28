"""
Core Steam API extraction logic
"""

import requests
import re
from datetime import datetime


def get_steam_tags_and_description(appid: int) -> tuple:
    try:
        url = f"https://store.steampowered.com/api/appdetails"
        params = {
            "appids": appid, 
            "filters": "categories,genres,short_description,detailed_description"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # Check if the request was successful
        if str(appid) not in data or not data[str(appid)]["success"]:
            return [], ""
        
        game_data = data[str(appid)]["data"]
        tags = []
        description = ""
        
        # Extract genres and categories as tags
        for data_type in ["genres", "categories"]:
            if data_type in game_data:
                for item in game_data[data_type]:
                    item_name = item["description"].lower()
                    
                    # Filter out less useful Steam categories
                    excluded_categories = [
                        "steam achievements", 
                        "steam cloud", 
                        "steam trading cards", 
                        "full controller support"
                    ]
                    
                    if data_type == "categories" and item_name in excluded_categories:
                        continue
                        
                    tags.append(item_name)
        
        # Get game description (prefer short, fallback to detailed)
        if "short_description" in game_data and game_data["short_description"]:
            description = game_data["short_description"]
        elif "detailed_description" in game_data and game_data["detailed_description"]:
            # Clean HTML tags and limit length
            description = re.sub(r'<[^>]+>', '', game_data["detailed_description"])
            if len(description) > 500:
                description = description[:500] + "..."
        
        return tags[:3], description  # Return max 3 tags
    
    except Exception as e:
        print(f"Error fetching Steam data for appid {appid}: {e}")
        return [], ""


def gather_steam_reviews(appid: int, count: int = 100) -> list:
    url = f"https://store.steampowered.com/appreviews/{appid}"
    params = {
        "json": 1,
        "num_per_page": count,
        "filter": "recent",  # Can be: recent, updated, all
        "language": "english"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "reviews" not in data:
            return []
            
        reviews = []
        for review in data["reviews"]:
            review_data = {
                "author_id": review["author"]["steamid"],
                "review": review["review"],
                "voted_up": review["voted_up"],  # True if positive review
                "playtime_hours": round(review["author"]["playtime_forever"] / 60, 1),
                "date": datetime.fromtimestamp(review["timestamp_created"]).isoformat(),
                "helpful_votes": review.get("votes_up", 0),
                "funny_votes": review.get("votes_funny", 0),
                "received_for_free": review.get("received_for_free", False),
                "written_during_early_access": review.get("written_during_early_access", False)
            }
            reviews.append(review_data)
            
        return reviews
    
    except Exception as e:
        print(f"Error fetching reviews for appid {appid}: {e}")
        return []


def get_basic_game_info(appid: int) -> dict:
    try:
        url = f"https://store.steampowered.com/api/appdetails"
        params = {
            "appids": appid,
            "filters": "basic"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if str(appid) not in data or not data[str(appid)]["success"]:
            return {}
            
        game_data = data[str(appid)]["data"]
        
        return {
            "name": game_data.get("name", "Unknown"),
            "appid": appid,
            "type": game_data.get("type", "unknown"),
            "is_free": game_data.get("is_free", False),
            "release_date": game_data.get("release_date", {}).get("date", "Unknown")
        }
        
    except Exception as e:
        print(f"Error fetching basic info for appid {appid}: {e}")
        return {}


# Example usage and testing
if __name__ == "__main__":
    test_appid = 620
    
    print(f"Testing Steam extraction for appid: {test_appid}")
    print("=" * 50)
    
    basic_info = get_basic_game_info(test_appid)
    
    print(f"Game: {basic_info.get('name', 'Unknown')}")
    print(f"Type: {basic_info.get('type', 'Unknown')}")
    print(f"Free: {basic_info.get('is_free', False)}")
    print(f"Release: {basic_info.get('release_date', 'Unknown')}")
    print()
    
    tags, description = get_steam_tags_and_description(test_appid)

    print(f"Tags: {', '.join(tags) if tags else 'None found'}")
    print(f"Description: {description[:100]}{'...' if len(description) > 100 else ''}")
    print()
    
    reviews = gather_steam_reviews(test_appid, 200) 

    print(f"Found {len(reviews)} reviews:")
    
    for i, review in enumerate(reviews):  # Show first 3
        print(f"\nReview {i}:")
        print(f"  Positive: {review['voted_up']}")
        print(f"  Playtime: {review['playtime_hours']} hours")
        print(f"  Text: {review['review'][:100]}...")