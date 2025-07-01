import requests
import time 
from datetime import datetime

class EndpointHandler:
    def __init__(self, appid=None):
        self.appid = appid
    
    def gather_steam_reviews(self, count=40, filter="recent"):
        target_appid = self.appid
        if not target_appid:
            raise ValueError("No appid provided. Set it in constructor or pass as parameter.")
        
        all_reviews = []
        cursor = "*"
        
        while len(all_reviews) < count:
            remaining = count - len(all_reviews)
            current_request_count = min(100, remaining)
            
class EndpointHandler:
    def __init__(self, appid=None):
        self.appid = appid
    
    def gather_steam_reviews(self, count=40, filter="recent"):
        # filter (str): Filter type - "recent", "updated", or "all" (default: "recent")
        target_appid = self.appid
        if not target_appid:
            raise ValueError("No appid provided. Set it in constructor or pass as parameter.")
            
        
        all_reviews = []
        cursor = "*"
        print(count)
        while len(all_reviews) < count: 
            remaining = count - len(all_reviews)
            current_request_count = min(100, remaining)

            url = f"https://store.steampowered.com/appreviews/{target_appid}"

            params = {
                "json": 1,
                "num_per_page": current_request_count,
                "filter": filter,
                "language": "english",
                "cursor" : cursor
            }
        
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()  # Raise exception for bad status codes
                data = response.json()
                
                if "reviews" not in data:
                    break
                
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
                    all_reviews.append(review_data)

                new_cursor = data.get("cursor")
                if not new_cursor or new_cursor == cursor: 
                    print(f"No more pages. Captured {len(all_reviews)} reviews")
                    break 
                cursor = new_cursor
                
                time.sleep(0.25)
            except requests.RequestException as e:
                print(f"Network error fetching reviews for appid {target_appid}: {e}")
                return []
            except Exception as e:
                print(f"Error fetching reviews for appid {target_appid}: {e}")
                return []
                
            
        return all_reviews   
    
# Convenience function for direct access (like pandas style)
def get_steam_reviews(appid, count=40, filter="recent"):
    handler = EndpointHandler(appid)
    return handler.gather_steam_reviews(count=count, filter=filter)