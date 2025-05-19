import json

# syntax stuff
from typing import List,Dict, Any
import logging 

def load_reviews_json(filename: str) -> List[Dict[str,Any]]: 
    try: 
        with open(filename, 'r', encoding = 'utf-8') as f: 
            return json.load(f)
    except Exception as e: 
        logging.error(f"Error loading JSON file: {e}")
        return []

def get_video_details(service, video_id: str) -> Dict[str, Any]:
    try:
        response = service.videos().list(
            part="snippet,topicDetails",
            id=video_id
        ).execute()
        
        if 'items' in response and len(response['items']) > 0:
            tags = response['items'][0]['snippet'].get('tags', [])
            
            # Get topic categories if available
            topics = {}
            if 'topicDetails' in response['items'][0] and 'topicCategories' in response['items'][0]['topicDetails']:
                topics = {url.split('/')[-1]: url for url in response['items'][0]['topicDetails']['topicCategories']}
            
            return {
                'tags': tags,
                'topics': topics
            }
        else:
            return {'tags': [], 'topics': {}}
    except Exception as e:
        print(f"Error getting video details for {video_id}: {e}")
        return {'tags': [], 'topics': {}}