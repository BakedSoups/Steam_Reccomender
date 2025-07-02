import requests
import time
import datetime
import re


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
                "cursor": cursor
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
                        "date": datetime.datetime.fromtimestamp(review["timestamp_created"]).isoformat(),
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
    
    def get_steam_tags(self):
        """
        Fetch Steam tags for the game using Steam's store API
        Returns a list of tag dictionaries with 'name' and 'count' (vote count)
        """
        target_appid = self.appid
        if not target_appid:
            raise ValueError("No appid provided. Set it in constructor or pass as parameter.")
        
        url = f"https://store.steampowered.com/app/{target_appid}"
        
        try:
            # First, get the main store page to extract tags
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Try to get tags from the store API endpoint
            api_url = "https://store.steampowered.com/api/appdetails"
            params = {
                "appids": target_appid,
                "filters": "categories,genres"
            }
            
            api_response = requests.get(api_url, params=params, timeout=10)
            api_response.raise_for_status()
            api_data = api_response.json()
            
            if str(target_appid) not in api_data or not api_data[str(target_appid)]["success"]:
                print(f"Could not fetch app details for appid {target_appid}")
                return []
            
            app_data = api_data[str(target_appid)]["data"]
            tags = []
            
            # Extract genres (which are like tags)
            if "genres" in app_data:
                for genre in app_data["genres"]:
                    tags.append({
                        "name": genre["description"],
                        "type": "genre"
                    })
            
            # Extract categories
            if "categories" in app_data:
                for category in app_data["categories"]:
                    tags.append({
                        "name": category["description"],
                        "type": "category"
                    })
            
            return tags
            
        except requests.RequestException as e:
            print(f"Network error fetching tags for appid {target_appid}: {e}")
            return []
        except Exception as e:
            print(f"Error fetching tags for appid {target_appid}: {e}")
            return []
    


# Convenience functions for direct access (like pandas style)
def get_steam_reviews(appid, count=40, filter="recent"):
    handler = EndpointHandler(appid)
    return handler.gather_steam_reviews(count=count, filter=filter)

def get_steam_tags(appid):
    handler = EndpointHandler(appid)
    return handler.get_steam_tags()
