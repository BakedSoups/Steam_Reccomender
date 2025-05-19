import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from googleapiclient.discovery import build
import time

def get_channel_info(service, channel_handle: str) -> Dict[str, str]:
    """Get the channel ID and uploads playlist ID from a channel handle."""
    response = service.channels().list(
        part='id,contentDetails',
        forHandle=channel_handle
    ).execute()
    
    if 'items' in response and len(response['items']) > 0:
        channel_id = response['items'][0]['id']
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        return {'channel_id': channel_id, 'uploads_playlist_id': uploads_playlist_id}
    else:
        raise ValueError(f"Channel with handle {channel_handle} not found")

def get_all_videos(service, uploads_playlist_id: str, search_term: str = None, max_results: int = None) -> List[Dict[str, Any]]:
    """
    Get all videos from a channel's uploads playlist, optionally filtering by a search term in the title.
    
    Args:
        service: YouTube API service object
        uploads_playlist_id: The ID of the channel's uploads playlist
        search_term: Optional term to filter video titles (case-insensitive)
        max_results: Maximum number of videos to return (None for all)
    
    Returns:
        List of video information dictionaries
    """
    videos = []
    next_page_token = None
    results_per_page = 50  # Maximum allowed by the API
    total_fetched = 0
    page_count = 0
    max_pages = 100  # Set a higher limit since we're looking for all videos
    
    print("Fetching videos from channel's uploads, this may take a while...")
    
    while True:
        page_count += 1
        print(f"Fetching page {page_count}...", end=" ", flush=True)
        
        try:
            request = service.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=results_per_page,
                pageToken=next_page_token
            )
            response = request.execute()
            
            items_count = len(response.get('items', []))
            total_fetched += items_count
            print(f"Got {items_count} videos")
            
            for item in response.get('items', []):
                title = item['snippet']['title']
                
                if search_term is None or search_term.lower() in title.lower():
                    video_info = {
                        'title': title,
                        'video_id': item['contentDetails']['videoId'],
                        'url': f"https://www.youtube.com/watch?v={item['contentDetails']['videoId']}",
                        'published_at': item['snippet']['publishedAt'],
                        'description': item['snippet']['description'],
                        'thumbnail': item['snippet']['thumbnails']['high']['url'] if 'thumbnails' in item['snippet'] else None
                    }
                    videos.append(video_info)
                    
                    # Print milestone for matching videos
                    if len(videos) % 10 == 0:
                        print(f"Found {len(videos)} matching videos so far...")
            
            # Get the next page token
            next_page_token = response.get('nextPageToken')
            
            # Stop conditions
            if not next_page_token:
                print("No more pages available.")
                break
                
            if max_results and len(videos) >= max_results:
                print(f"Reached requested maximum of {max_results} matching videos.")
                break
                
            if page_count >= max_pages:
                print(f"Reached maximum page limit of {max_pages}. To get more videos, increase the max_pages value.")
                break
                
            # Small delay to avoid hitting rate limits
            time.sleep(0.3)
            
        except Exception as e:
            print(f"\nError fetching page {page_count}: {e}")
            break
    
    # If max_results is specified, truncate the list
    if max_results and len(videos) > max_results:
        videos = videos[:max_results]
        
    print(f"\nTotal: Fetched {total_fetched} videos across {page_count} pages, found {len(videos)} matching videos")
    return videos

def save_videos_to_json(videos: List[Dict[str, Any]], filename: str):
    """Save the list of videos to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(videos)} videos to {filename}")

def main():
    # Load API key from environment variables
    load_dotenv()
    api_key = os.getenv("YT_API_KEY")
    
    if not api_key:
        print("Error: YouTube API key not found. Please set YT_API_KEY environment variable.")
        return
    
    # Build YouTube API service
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # Channel handle (e.g., @gameranxTV)
    channel_handle = input("Enter channel handle (e.g., @gameranxTV): ")
    
    # Get channel info
    try:
        channel_info = get_channel_info(youtube, channel_handle)
        print(f"Channel ID: {channel_info['channel_id']}")
        print(f"Uploads Playlist ID: {channel_info['uploads_playlist_id']}")
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Search term - default to "before you buy" but allow customization
    default_search = "before you buy"
    search_input = input(f"Search term (press Enter for '{default_search}'): ")
    search_term = search_input if search_input.strip() else default_search
    
    # Optional: limit the number of results
    try:
        max_results_input = input("Maximum number of videos to return (press Enter for all): ")
        if max_results_input.strip().lower() == 'all':
            max_results = None
        else:
            max_results = int(max_results_input) if max_results_input.strip() else None
    except ValueError:
        print("Invalid input, fetching all videos.")
        max_results = None
    
    # Get videos
    videos = get_all_videos(youtube, channel_info['uploads_playlist_id'], search_term, max_results)
    
    # Sort videos by date (newest first)
    videos.sort(key=lambda x: x['published_at'], reverse=True)
    
    # Display results
    if videos:
        print(f"\nFound {len(videos)} videos containing '{search_term}':")
        for i, video in enumerate(videos, 1):
            print(f"{i}. {video['title']}")
            print(f"   URL: {video['url']}")
            print(f"   Published: {video['published_at']}")
            print()
        
        # Save to JSON
        save_option = input("Save results to JSON? (y/n): ").lower().strip()
        if save_option == 'y':
            default_filename = f"{channel_handle.replace('@', '')}_{search_term.replace(' ', '_')}_videos.json"
            filename_input = input(f"Filename (press Enter for '{default_filename}'): ")
            filename = filename_input.strip() if filename_input.strip() else default_filename
            save_videos_to_json(videos, filename)
    else:
        print(f"No videos found containing '{search_term}'")
        
if __name__ == "__main__":
    main()