import requests
from datetime import datetime

class EndpointHandler:
    def __init__(self, appid=None):
        self.appid = appid
    
    def gather_steam_reviews(self, appid=None, count=40, filter="recent"):
        """
        Gather Steam reviews for a given app
        
        Args:
            appid (int): Steam app ID (uses self.appid if not provided)
            count (int): Number of reviews to fetch (default: 40)
            filter (str): Filter type - "recent", "updated", or "all" (default: "recent")
        
        Returns:
            list: List of review dictionaries
        """
        # Use provided appid or fall back to instance appid
        target_appid = appid or self.appid
        if not target_appid:
            raise ValueError("No appid provided. Set it in constructor or pass as parameter.")
            
        url = f"https://store.steampowered.com/appreviews/{target_appid}"
        
        params = {
            "json": 1,
            "num_per_page": count,
            "filter": filter,
            "language": "english"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # Raise exception for bad status codes
            data = response.json()
            
            if "reviews" not in data:
                return []
            
            reviews = []
            for review in data["reviews"]:
                review_data = {
                    "author_id": review["author"]["steamid"],
                    "review": review["review"],
                    "voted_up": review["voted_up"],
                    "playtime_hours": round(review["author"]["playtime_forever"] / 60, 1),
                    "date": datetime.fromtimestamp(review["timestamp_created"]).isoformat(),
                    "helpful_votes": review.get("votes_up", 0),
                    "funny_votes": review.get("votes_funny", 0),
                    "received_for_free": review.get("received_for_free", False),
                    "written_during_early_access": review.get("written_during_early_access", False)
                }
                reviews.append(review_data)
            
            return reviews
            
        except requests.RequestException as e:
            print(f"Network error fetching reviews for appid {target_appid}: {e}")
            return []
        except Exception as e:
            print(f"Error fetching reviews for appid {target_appid}: {e}")
            return []

# Convenience function for direct access (like pandas style)
def get_steam_reviews(appid, count=40, filter="recent"):
    """
    Direct function to get Steam reviews without creating a class instance
    Usage: sapi.get_steam_reviews(appid=123456)
    """
    handler = EndpointHandler(appid)
    return handler.gather_steam_reviews(count=count, filter=filter)