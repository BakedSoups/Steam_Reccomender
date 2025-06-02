import requests
import json
import time
import logging

def steam_api_pull(app_id):
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                wait_time = 30
                
                if retry_after:
                    try:
                        wait_time = int(retry_after)
                    except ValueError:
                        pass
                
                logging.warning(f"Rate limited for app {app_id}. Waiting {wait_time}s before retry {attempt+1}/{max_retries}")
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                logging.error(f"Bad status for app {app_id}: {response.status_code}")
                return "", "", "", "", "", "", "", "", ""
            
            if response.text.startswith("<"):
                logging.warning(f"Got HTML response for app {app_id}, likely rate limited or invalid ID")
                time.sleep(5)
                continue
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON for app {app_id}")
                return "", "", "", "", "", "", "", "", ""
            
            app_data = data.get(str(app_id))
            if not app_data or not app_data.get('success'):
                logging.warning(f"API returned success=false for app {app_id}")
                return "", "", "", "", "", "", "", "", ""
            
            info = app_data.get('data', {})
            
            genre_list = [g['description'] for g in info.get('genres', [])]
            genre = ", ".join(genre_list)
            
            description = info.get('short_description', '')
            website = info.get('website', '')
            header_image = info.get('header_image', '')
            background = info.get('background', '')
            
            screenshot = ""
            screenshots = info.get('screenshots', [])
            if screenshots:
                screenshot = screenshots[0].get('path_full', '')
            
            steam_url = f"https://store.steampowered.com/app/{app_id}"
            
            price_overview = info.get('price_overview', {})
            pricing = price_overview.get('final_formatted', '')
            
            achievements_data = info.get('achievements', {})
            total_achievements = achievements_data.get('total', 0)
            achievements = f"{total_achievements} achievements" if total_achievements > 0 else "0 achievements"
            
            return genre, description, website, header_image, background, screenshot, steam_url, pricing, achievements
            
        except requests.RequestException as e:
            logging.error(f"Request failed for app {app_id}: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return "", "", "", "", "", "", "", "", ""
    
    return "", "", "", "", "", "", "", "", ""